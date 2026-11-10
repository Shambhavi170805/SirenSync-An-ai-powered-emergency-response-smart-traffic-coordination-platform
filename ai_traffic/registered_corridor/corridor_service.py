"""Join upstream dispatch, registered plate confirmation, GPS proximity, and signals."""

import math
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional

from ai_traffic.registered_corridor.registry import VehicleRegistry, normalize_plate
from ai_traffic.registered_corridor.signals import SimulatedSignalController


def distance_m(a: dict, b: dict) -> float:
    radius = 6_371_000
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat = lat2 - lat1
    dlng = math.radians(b["lng"] - a["lng"])
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _route_measure(points: list[dict], target: dict) -> tuple[float, float]:
    """Return the nearest route distance and its distance from the target point."""
    cumulative = 0.0
    best_along, best_separation = 0.0, float("inf")
    for start, end in zip(points, points[1:]):
        segment_length = distance_m(start, end)
        if segment_length <= 0:
            continue
        # Local equirectangular coordinates are accurate enough for this short pilot corridor.
        mean_lat = math.radians((start["lat"] + end["lat"] + target["lat"]) / 3)
        scale_x = 6_371_000 * math.cos(mean_lat) * math.pi / 180
        scale_y = 6_371_000 * math.pi / 180
        sx, sy = start["lng"] * scale_x, start["lat"] * scale_y
        ex, ey = end["lng"] * scale_x, end["lat"] * scale_y
        tx, ty = target["lng"] * scale_x, target["lat"] * scale_y
        dx, dy = ex - sx, ey - sy
        fraction = max(0.0, min(1.0, ((tx - sx) * dx + (ty - sy) * dy) / (dx * dx + dy * dy)))
        px, py = sx + fraction * dx, sy + fraction * dy
        separation = math.hypot(tx - px, ty - py)
        if separation < best_separation:
            best_separation = separation
            best_along = cumulative + fraction * segment_length
        cumulative += segment_length
    return best_along, best_separation


class CorridorService:
    def __init__(self, config: dict, registry: VehicleRegistry, emit: Callable[[str, dict], None]):
        self.config = config
        self.registry = registry
        self.emit = emit
        self.junctions = {item["junction_id"]: item for item in config.get("junctions", [])}
        self.signals = SimulatedSignalController(
            config["signal_timing_seconds"], config["normal_cycle"], emit,
            {item["junction_id"]: item.get("ambulance_direction", "north_south") for item in config.get("junctions", [])},
        )
        self._lock = threading.RLock()
        self._routes: dict[str, dict] = {}
        self._stop = threading.Event()
        self._ticker: Optional[threading.Thread] = None

    def register_junctions(self, junctions: list[dict]) -> None:
        """Install only the intersections found on the currently selected route."""
        with self._lock:
            for junction in junctions:
                junction_id = junction["junction_id"]
                self.junctions[junction_id] = dict(junction)
                self.signals.register_junction(junction)

    def start(self) -> None:
        self._stop.clear()
        self._ticker = threading.Thread(target=self._tick, name="corridor-signal-timer", daemon=True)
        self._ticker.start()

    def stop(self) -> None:
        self._stop.set()
        if self._ticker and self._ticker.is_alive():
            self._ticker.join(timeout=2)

    def _tick(self) -> None:
        while not self._stop.wait(.1):
            self.signals.tick()

    def allocate_route(self, payload: dict) -> dict:
        ambulance_id = payload["ambulance_id"].strip()
        plate = normalize_plate(payload["vehicle_number"])
        if not self.registry.matches(ambulance_id, plate):
            raise ValueError("vehicle_number is not registered to this ambulance_id")
        registration = self.registry.find_plate(plate) or {}
        points = [dict(point) for point in (payload.get("route_points") or [])]
        if not points and payload.get("origin") and payload.get("destination"):
            points = self._fallback_points(payload["origin"], payload["destination"])
        if len(points) < 2:
            raise ValueError("route_points must contain at least an origin and destination")
        requested = payload.get("junctions") or []
        if not requested:
            raise ValueError("junctions must list the configured junctions on this route, in travel order")
        unknown = [junction for junction in requested if junction not in self.junctions]
        if unknown:
            raise ValueError(f"Unknown configured junction(s): {', '.join(unknown)}")
        junction_measures = {
            junction_id: _route_measure(points, self.junctions[junction_id])
            for junction_id in requested
        }
        max_junction_offset = float(self.config.get("max_junction_route_offset_m", 120))
        too_far = [junction_id for junction_id, (_, offset) in junction_measures.items()
                   if offset > max_junction_offset]
        if too_far:
            raise ValueError(
                f"Junction(s) {', '.join(too_far)} are more than {max_junction_offset:.0f} m "
                "from the supplied route polyline"
            )
        ordered_distances = [junction_measures[junction_id][0] for junction_id in requested]
        if ordered_distances != sorted(ordered_distances):
            raise ValueError("junctions must be listed in the order the ambulance reaches them")
        with self._lock:
            old = self._routes.get(ambulance_id)
            if old:
                self._release_route(old, "ROUTE_REPLACED")
            route = {
                "ambulance_id": ambulance_id,
                "vehicle_number": plate,
                "emergency_id": payload.get("emergency_id"),
                "hospital_id": payload.get("hospital_id"),
                "hospital_name": payload.get("hospital_name"),
                "is_simulated": (
                    payload.get("is_simulated")
                    if payload.get("is_simulated") is not None
                    else registration.get("is_simulated", True)
                ),
                "junctions": requested,
                "route_points": points,
                # Snap each configured junction to the actual supplied road polyline.
                # This makes pass/release timing follow route geometry, not junction count.
                "junction_route_m": {
                    junction_id: round(junction_measures[junction_id][0], 1)
                    for junction_id in requested
                },
                "emergency_severity": payload.get("emergency_severity", "CRITICAL"),
                "progress_percent": 0.0,
                "current_lat": points[0]["lat"],
                "current_lng": points[0]["lng"],
                "plate_confirmed": False,
                "triggered_junctions": [],
                "passed_junctions": [],
                "status": "ACTIVE",
                "allocated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._routes[ambulance_id] = route
        self.emit("ROUTE_ALLOCATED", {
            "ambulance_id": ambulance_id,
            "vehicle_number": plate,
            "hospital_id": payload.get("hospital_id"),
            "hospital_name": payload.get("hospital_name"),
            "junctions": requested,
            "status": "ACTIVE",
        })
        return self._public_route(route)

    def confirm_plate(self, camera_id: str, junction_id: str, observed: str, confidence: float, source: str) -> dict:
        match = self.registry.find_plate(observed)
        with self._lock:
            route = self._routes.get(match["ambulance_id"]) if match else None
            if not match or not route or route["status"] != "ACTIVE" or junction_id not in route["junctions"]:
                self.emit("PLATE_REJECTED", {
                    "camera_id": camera_id,
                    "junction_id": junction_id,
                    "observed_plate": normalize_plate(observed),
                    "confidence": confidence,
                    "reason": "PLATE_NOT_REGISTERED_OR_NO_ACTIVE_ROUTE",
                })
                return {"verified": False, "reason": "No matching active route for this registered plate."}
            if route["plate_confirmed"]:
                return {"verified": True, "ambulance_id": route["ambulance_id"], "duplicate": True}
            route["plate_confirmed"] = True
            self.emit("PLATE_VERIFIED", {
                "camera_id": camera_id,
                "junction_id": junction_id,
                "ambulance_id": route["ambulance_id"],
                "vehicle_number": route["vehicle_number"],
                "confidence": round(confidence, 1),
                "source": source,
            })
            # The camera sits on the configured approach to this junction. A verified
            # plate can begin clearing the conflicting green before the ambulance arrives.
            self._request_corridor(route, junction_id, "REGISTERED_PLATE_CAMERA_CONFIRMED")
            return {"verified": True, "ambulance_id": route["ambulance_id"], "junction_id": junction_id}

    def update_progress(self, ambulance_id: str, progress_percent: float,
                        current_lat: Optional[float] = None, current_lng: Optional[float] = None,
                        is_simulated: Optional[bool] = None, source: str = "DIRECT_API") -> dict:
        with self._lock:
            route = self._routes.get(ambulance_id)
            if not route or route["status"] != "ACTIVE":
                raise KeyError(f"No active allocated route for {ambulance_id}")
            has_gps = current_lat is not None and current_lng is not None
            if not has_gps:
                current_lat, current_lng = self._interpolate(route["route_points"], progress_percent)
                progress_percent = max(route["progress_percent"], min(100.0, float(progress_percent)))
            else:
                route_length = self._route_distance(route["route_points"], 100.0)
                gps_distance, deviation = _route_measure(
                    route["route_points"], {"lat": current_lat, "lng": current_lng}
                )
                allowed_deviation = float(self.config.get("max_route_deviation_m", 120))
                if deviation > allowed_deviation:
                    raise ValueError(
                        f"GPS point is {deviation:.0f} m from the allocated route; "
                        "send a corrected route allocation before continuing"
                    )
                gps_progress = 100.0 * gps_distance / route_length if route_length else 0.0
                # When GPS is present, derive progress from the road polyline so a
                # stale percentage cannot advance the corridor ahead of the vehicle.
                progress_percent = max(route["progress_percent"], min(100.0, gps_progress))
            route.update({
                "progress_percent": progress_percent,
                "current_lat": current_lat,
                "current_lng": current_lng,
            })
            if is_simulated is not None:
                route["is_simulated"] = is_simulated
            current = {"lat": current_lat, "lng": current_lng}
            travelled_m = self._route_distance(route["route_points"], progress_percent)
            for junction_id in route["junctions"]:
                junction = self.junctions[junction_id]
                separation = distance_m(current, junction)
                if junction_id in route["triggered_junctions"] and junction_id not in route["passed_junctions"]:
                    junction_m = route["junction_route_m"][junction_id]
                    if travelled_m >= junction_m + float(self.config.get("passed_distance_m", 45)):
                        route["passed_junctions"].append(junction_id)
                        self.signals.release_corridor(junction_id, ambulance_id, "AMBULANCE_PASSED_JUNCTION")
                        self.emit("JUNCTION_PASSED", {"ambulance_id": ambulance_id, "junction_id": junction_id, "progress_percent": progress_percent})
                elif route["plate_confirmed"] and junction_id not in route["passed_junctions"] and separation <= self.config["approach_distance_m"]:
                    self._request_corridor(route, junction_id, "GPS_APPROACH_CONFIRMED")
            if progress_percent >= 100:
                route["status"] = "COMPLETED"
                self._release_route(route, "ROUTE_COMPLETED")
            public = self._public_route(route)
        self.emit("ROUTE_UPDATED", {
            "ambulance_id": ambulance_id,
            "vehicle_number": route["vehicle_number"],
            "progress_percent": progress_percent,
            "current_lat": current_lat,
            "current_lng": current_lng,
            "status": route["status"],
            "is_simulated": route.get("is_simulated", True),
            "source": source,
        })
        return public

    def _request_corridor(self, route: dict, junction_id: str, reason: str) -> None:
        if junction_id in route["triggered_junctions"]:
            return
        self.signals.request_corridor(junction_id, route["ambulance_id"], route["vehicle_number"])
        route["triggered_junctions"].append(junction_id)
        self.emit("CORRIDOR_REQUESTED", {
            "ambulance_id": route["ambulance_id"],
            "vehicle_number": route["vehicle_number"],
            "junction_id": junction_id,
            "reason": reason,
        })

    def _release_route(self, route: dict, reason: str) -> None:
        for junction_id in route["triggered_junctions"]:
            if junction_id not in route["passed_junctions"]:
                self.signals.release_corridor(junction_id, route["ambulance_id"], reason)
                route["passed_junctions"].append(junction_id)

    def end_route(self, ambulance_id: str, status: str, reason: str) -> Optional[dict]:
        """End an upstream route on arrival or a terminal ambulance state."""
        with self._lock:
            route = self._routes.get(ambulance_id)
            if not route or route["status"] != "ACTIVE":
                return None
            route["status"] = status
            self._release_route(route, reason)
            public = self._public_route(route)
        self.emit("ROUTE_ENDED", {
            "ambulance_id": ambulance_id,
            "vehicle_number": route["vehicle_number"],
            "status": status,
            "reason": reason,
        })
        return public

    @staticmethod
    def _interpolate(points: list[dict], progress: float) -> tuple[float, float]:
        """Interpolate by travelled distance so the demo follows the route polyline."""
        if len(points) < 2:
            return points[0]["lat"], points[0]["lng"]
        lengths = [distance_m(points[index], points[index + 1]) for index in range(len(points) - 1)]
        total = sum(lengths)
        if total <= 0:
            return points[0]["lat"], points[0]["lng"]
        target = total * max(0.0, min(100.0, progress)) / 100.0
        for index, length in enumerate(lengths):
            if target <= length or index == len(lengths) - 1:
                fraction = target / length if length else 0.0
                start, end = points[index], points[index + 1]
                return (start["lat"] + fraction * (end["lat"] - start["lat"]),
                        start["lng"] + fraction * (end["lng"] - start["lng"]))
            target -= length
        return points[-1]["lat"], points[-1]["lng"]

    @staticmethod
    def _route_distance(points: list[dict], progress: float) -> float:
        lengths = [distance_m(points[index], points[index + 1]) for index in range(len(points) - 1)]
        return sum(lengths) * max(0.0, min(100.0, progress)) / 100.0

    @staticmethod
    def _fallback_points(origin: str, destination: str) -> list[dict]:
        """Accept the shared origin/destination shape when a route polyline is absent."""
        try:
            start = [float(value.strip()) for value in origin.split(",")]
            end = [float(value.strip()) for value in destination.split(",")]
            if len(start) != 2 or len(end) != 2:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("origin and destination must use 'latitude,longitude'")
        return [{
            "lat": start[0] + (end[0] - start[0]) * i / 20,
            "lng": start[1] + (end[1] - start[1]) * i / 20,
        } for i in range(21)]

    @staticmethod
    def _public_route(route: dict) -> dict:
        # The dashboard needs the dispatch polyline to draw and animate the road route.
        return dict(route)

    def get_route(self, ambulance_id: str) -> Optional[dict]:
        with self._lock:
            route = self._routes.get(ambulance_id)
            return self._public_route(route) if route else None

    def list_routes(self) -> list[dict]:
        with self._lock:
            return [self._public_route(route) for route in self._routes.values()]

    def demo_progress(self, ambulance_id: str) -> None:
        """Feed mock GPS updates for the dashboard demo; production uses Nidhi telemetry."""
        for progress in range(5, 101, 5):
            time.sleep(1.0)
            try:
                self.update_progress(ambulance_id, progress)
            except KeyError:
                return
