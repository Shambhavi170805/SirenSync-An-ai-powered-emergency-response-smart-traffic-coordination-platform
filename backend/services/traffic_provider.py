from abc import ABC, abstractmethod
from typing import Tuple

class ITrafficProvider(ABC):
    """
    Abstract interface for traffic delay estimation.
    Allows swappable implementations (Mock vs future external APIs).
    """

    @abstractmethod
    def get_traffic_factor(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float
    ) -> Tuple[float, str]:
        """
        Returns a tuple of:
          - congestion_factor (float >= 1.0, where 1.0 is no delay, 1.3 is +30% transit delay)
          - description/explanation string
        """
        pass

class MockTrafficProvider(ITrafficProvider):
    """
    Deterministic Mock Traffic Provider.
    Zero external dependencies, zero API keys, 100% reproducible.
    Computes deterministic congestion based on coordinates and simulated corridor profiles.
    """

    def __init__(self):
        # Specific route overrides for deterministic test scenarios
        self._overrides = {}

    def set_override(self, hospital_id: str, factor: float, description: str):
        """Allows test scenarios to set deterministic traffic conditions."""
        self._overrides[hospital_id] = (factor, description)

    def clear_overrides(self):
        self._overrides.clear()

    def get_traffic_factor(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float
    ) -> Tuple[float, str]:
        # Deterministic calculation using coordinate hash
        # Simulates urban congestion variations in a 1.05 to 1.45 range
        coord_sum = abs(origin_lat * 1000 + origin_lng * 1000 + dest_lat * 1000 + dest_lng * 1000)
        bucket = int(coord_sum) % 5

        if bucket == 0:
            return 1.05, "Low traffic corridor (minimal delay +5%)"
        elif bucket == 1:
            return 1.15, "Moderate arterial traffic (+15% delay)"
        elif bucket == 2:
            return 1.25, "Suburban corridor with steady flow (+25% delay)"
        elif bucket == 3:
            return 1.35, "Dense urban junction delay (+35% delay)"
        else:
            return 1.45, "High congestion bottleneck (+45% delay)"

class GoogleRoutesTrafficProvider:
    """Google Routes API adapter for traffic-aware driving routes.

    Requires a billing-enabled Google Cloud project with Routes API enabled.
    The API key stays on the backend and is never sent to browser clients.
    """

    endpoint = "https://routes.googleapis.com/directions/v2:computeRoutes"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_traffic_factor(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float):
        """Synchronous traffic-aware duration ratio used by hospital ranking."""
        import httpx
        from datetime import datetime, timezone
        body = {
            "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
            "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
            "departureTime": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.duration,routes.staticDuration",
        }
        try:
            with httpx.Client(timeout=12.0) as client:
                response = client.post(self.endpoint, json=body, headers=headers)
                response.raise_for_status()
                route = (response.json().get("routes") or [])[0]
            traffic_seconds = float(str(route.get("duration", "0s")).rstrip("s"))
            freeflow_seconds = float(str(route.get("staticDuration", "0s")).rstrip("s"))
            factor = max(1.0, traffic_seconds / max(1.0, freeflow_seconds))
            return factor, f"Google Routes live traffic-aware driving time ({round(traffic_seconds / 60)} min vs {round(freeflow_seconds / 60)} min free-flow)"
        except Exception as exc:
            # Keep hospital ranking available, but do not silently substitute
            # mock traffic when Google was explicitly configured.
            return 1.0, f"Live traffic unavailable for this hospital route; neutral traffic factor used ({type(exc).__name__})"

    async def compute_route(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float):
        import httpx
        from datetime import datetime, timezone

        body = {
            "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
            "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
            "departureTime": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "polylineEncoding": "ENCODED_POLYLINE",
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.travelAdvisory.speedReadingIntervals",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(self.endpoint, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        routes = data.get("routes") or []
        if not routes:
            raise RuntimeError("Google Routes API returned no driving route.")
        route = routes[0]
        duration = route.get("duration", "0s")
        try:
            duration_seconds = float(str(duration).rstrip("s"))
        except ValueError:
            duration_seconds = 0.0
        intervals = (route.get("travelAdvisory") or {}).get("speedReadingIntervals") or []
        traffic_levels = {item.get("speed") for item in intervals if item.get("speed")}
        return {
            "provider": "Google Routes API",
            "trafficAware": True,
            "trafficSummary": ", ".join(sorted(traffic_levels)) if traffic_levels else "Traffic-aware route",
            "speedReadingIntervals": intervals,
            "distanceMeters": route.get("distanceMeters"),
            "durationSeconds": duration_seconds,
            "staticDuration": route.get("staticDuration"),
            "encodedPolyline": (route.get("polyline") or {}).get("encodedPolyline"),
        }


def build_default_traffic_provider():
    import os
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    provider_mode = os.getenv("TRAFFIC_PROVIDER", "google" if api_key else "mock").strip().lower()
    if provider_mode == "google" and api_key:
        return GoogleRoutesTrafficProvider(api_key)
    return MockTrafficProvider()


# Selected once at process startup. Configure GOOGLE_MAPS_API_KEY before Uvicorn starts.
default_traffic_provider = build_default_traffic_provider()

