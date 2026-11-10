"""OSM road routing plus route-specific junction extraction for the pilot area."""

import math
import os


def _distance_m(a: dict, b: dict) -> float:
    radius = 6_371_000
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat = lat2 - lat1
    dlng = math.radians(b["lng"] - a["lng"])
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


class OSMRoutePlanner:
    """Request actual road geometry and intersections for a chosen hospital route."""

    def __init__(self):
        self.base_url = os.getenv("SIRENSYNC_ROUTER_BASE_URL", "https://router.project-osrm.org").rstrip("/")

    async def plan(self, origin: dict, destination: dict) -> list[dict]:
        import httpx

        coordinates = (
            f"{origin['lng']},{origin['lat']};"
            f"{destination['longitude']},{destination['latitude']}"
        )
        url = f"{self.base_url}/route/v1/driving/{coordinates}"
        async with httpx.AsyncClient(timeout=18.0) as client:
            response = await client.get(url, params={
                "alternatives": "2",
                "steps": "true",
                "overview": "full",
                "geometries": "geojson",
            })
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError(f"Road router returned {data.get('code', 'no route')}")

        options = []
        for route_index, route in enumerate(data["routes"][:3]):
            coords = route.get("geometry", {}).get("coordinates", [])
            route_points = [{"lat": float(lat), "lng": float(lon)} for lon, lat in coords]
            if len(route_points) < 2:
                continue
            junctions = self._extract_junctions(route)
            if not junctions:
                raise ValueError("The selected road route returned no junctions; try another hospital or route")
            options.append({
                "option_index": len(options),
                "summary": route.get("legs", [{}])[0].get("summary") or f"OSM road route {route_index + 1}",
                "distance_m": round(float(route.get("distance", 0))),
                "duration_s": round(float(route.get("duration", 0))),
                "route_points": route_points,
                "junctions": junctions,
                "junction_ids": [item["junction_id"] for item in junctions],
            })
        if not options:
            raise ValueError("Road router returned no usable route geometry")
        return options

    async def match_supplied_route(self, supplied_points: list[dict]) -> dict:
        """Snap an upstream selected route to roads and discover its junctions.

        This preserves Shambhavi's route choice. OSRM map matching is used to
        obtain road geometry and intersections; it is not asked to find a new
        origin-to-destination alternative.
        """
        import httpx

        points = self._sample_points(supplied_points, limit=80)
        coordinates = ";".join(f"{point['lng']},{point['lat']}" for point in points)
        url = f"{self.base_url}/match/v1/driving/{coordinates}"
        async with httpx.AsyncClient(timeout=18.0) as client:
            response = await client.get(url, params={
                "steps": "true",
                "overview": "full",
                "geometries": "geojson",
                "gaps": "ignore",
                "tidy": "false",
                "radiuses": ";".join(["60"] * len(points)),
            })
        response.raise_for_status()
        data = response.json()
        matchings = data.get("matchings") or []
        tracepoints = data.get("tracepoints") or []
        if data.get("code") != "Ok" or not matchings:
            raise ValueError(f"Selected route could not be matched to roads ({data.get('code', 'no match')})")
        if len(matchings) != 1 or any(point is None for point in tracepoints):
            raise ValueError("Selected route could not be matched continuously; provide its road-route points")

        matched = matchings[0]
        coordinates = matched.get("geometry", {}).get("coordinates", [])
        route_points = [{"lat": float(lat), "lng": float(lon)} for lon, lat in coordinates]
        if len(route_points) < 2:
            raise ValueError("Selected route did not produce usable road geometry")
        junctions = self._extract_junctions(matched)
        if not junctions:
            raise ValueError("No junctions were found on the selected route")
        return {
            "option_index": 0,
            "summary": "Shambhavi selected route · map-matched to roads",
            "distance_m": round(float(matched.get("distance", 0))),
            "duration_s": round(float(matched.get("duration", 0))),
            "route_points": route_points,
            "junctions": junctions,
            "junction_ids": [item["junction_id"] for item in junctions],
            "route_source": "SHAMBHAVI_SELECTED_ROUTE",
        }

    @staticmethod
    def _sample_points(points: list[dict], limit: int) -> list[dict]:
        """Keep the whole route span while limiting OSRM's coordinate count."""
        if len(points) <= limit:
            return points
        last = len(points) - 1
        indexes = sorted({round(index * last / (limit - 1)) for index in range(limit)})
        return [points[index] for index in indexes]

    @staticmethod
    def _extract_junctions(route: dict) -> list[dict]:
        found = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                step_name = step.get("name") or "Road junction"
                maneuver = step.get("maneuver") or {}
                maneuver_type = str(maneuver.get("type", "")).lower()
                for intersection in step.get("intersections", []):
                    location = intersection.get("location") or []
                    bearings = intersection.get("bearings") or []
                    # A road intersection is where the routable network offers at least
                    # three directions; route bends without a joining road are ignored.
                    if len(location) != 2 or len(bearings) < 3:
                        continue
                    item = {"lat": float(location[1]), "lng": float(location[0])}
                    if any(_distance_m(item, existing) < 30 for existing in found):
                        continue
                    out_index = intersection.get("out")
                    bearing = bearings[out_index] if isinstance(out_index, int) and out_index < len(bearings) else 0
                    direction = "east_west" if 45 <= bearing < 135 or 225 <= bearing < 315 else "north_south"
                    item.update({
                        "junction_id": f"J-{item['lat']:.5f}-{item['lng']:.5f}",
                        "name": step_name if step_name != "Road junction" else f"Intersection {len(found) + 1}",
                        "ambulance_direction": direction,
                        "source": "OPENSTREETMAP_ROUTE_INTERSECTION",
                    })
                    found.append(item)

        # OSRM may omit bearing options at a mapped turn. Use actual maneuver points
        # as a fallback, still sourced from the selected road route rather than a demo list.
        if not found:
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    maneuver = step.get("maneuver") or {}
                    if str(maneuver.get("type", "")).lower() not in {"turn", "fork", "end of road", "roundabout", "rotary"}:
                        continue
                    location = maneuver.get("location") or []
                    if len(location) != 2:
                        continue
                    item = {"lat": float(location[1]), "lng": float(location[0])}
                    if any(_distance_m(item, existing) < 30 for existing in found):
                        continue
                    item.update({
                        "junction_id": f"J-{item['lat']:.5f}-{item['lng']:.5f}",
                        "name": step.get("name") or f"Intersection {len(found) + 1}",
                        "ambulance_direction": "north_south",
                        "source": "OPENSTREETMAP_ROUTE_MANEUVER",
                    })
                    found.append(item)
        return found
