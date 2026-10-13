"""
Google Maps Directions API Client and Polyline Decoder.
Fetches real routing itineraries from Google Maps Platform or falls back to
geometric interpolation when API keys are not supplied.
"""

from typing import Any, Dict, List, Tuple
import requests

from ai_traffic.core.logger import logger


def decode_polyline(polyline_str: str) -> List[Tuple[float, float]]:
    """
    Decodes Google Maps Encoded Polyline algorithm into list of (lat, lng) tuples.
    """
    points = []
    index = 0
    lat = 0
    lng = 0
    length = len(polyline_str)

    while index < length:
        # Decode latitude
        shift = 0
        result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        # Decode longitude
        shift = 0
        result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        points.append((lat / 1e5, lng / 1e5))

    return points


class GoogleMapsDirectionsClient:
    """
    Queries Google Maps Directions API or produces interpolated routing points.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"

    def get_route(
        self,
        origin: str,
        destination: str,
        waypoints: List[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches route geometry, distance, and duration.
        """
        if self.api_key and self.api_key != "YOUR_GOOGLE_MAPS_API_KEY_HERE":
            try:
                params = {
                    "origin": origin,
                    "destination": destination,
                    "key": self.api_key,
                    "mode": "driving"
                }
                if waypoints:
                    params["waypoints"] = "|".join(waypoints)

                logger.info(f"[GMAPS API] Querying Directions API: {origin} -> {destination}")
                resp = requests.get(self.base_url, params=params, timeout=6.0)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "OK" and data.get("routes"):
                        route = data["routes"][0]
                        overview_poly = route.get("overview_polyline", {}).get("points", "")
                        points = decode_polyline(overview_poly) if overview_poly else []
                        leg = route.get("legs", [{}])[0]

                        return {
                            "is_live_api": True,
                            "points": [{"lat": p[0], "lng": p[1]} for p in points],
                            "distance_meters": leg.get("distance", {}).get("value", 0),
                            "duration_seconds": leg.get("duration", {}).get("value", 0),
                            "summary": route.get("summary", "Google Maps Route"),
                            "status": "OK"
                        }
                    else:
                        logger.warning(f"[GMAPS API] Response status: {data.get('status')}. Using fallback routing.")
            except Exception as e:
                logger.warning(f"[GMAPS API] Error connecting to Google Maps Directions API ({e}). Falling back.")

        # Fallback Mock Interpolation
        logger.info(f"[ROUTING] Generating synthesized route geometry between {origin} and {destination}")
        return self._generate_fallback_route(origin, destination)

    def _generate_fallback_route(self, origin: str, destination: str) -> Dict[str, Any]:
        # Try to parse lat,lng strings
        try:
            o_lat, o_lng = [float(v.strip()) for v in origin.split(",")]
        except Exception:
            o_lat, o_lng = 12.9650, 77.5850

        try:
            d_lat, d_lng = [float(v.strip()) for v in destination.split(",")]
        except Exception:
            d_lat, d_lng = 12.9850, 77.6150

        # Synthesize 25 intermediate trajectory points
        steps = 25
        points = []
        for i in range(steps + 1):
            ratio = i / float(steps)
            lat = o_lat + ratio * (d_lat - o_lat)
            lng = o_lng + ratio * (d_lng - o_lng)
            points.append({"lat": round(lat, 5), "lng": round(lng, 5)})

        return {
            "is_live_api": False,
            "points": points,
            "distance_meters": 4200,
            "duration_seconds": 480,
            "summary": "Synthesized Emergency Transit Path (No Google API key configured)",
            "status": "FALLBACK"
        }
