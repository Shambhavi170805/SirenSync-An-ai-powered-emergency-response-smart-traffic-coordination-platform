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


class CorridorService:
    def __init__(self, config: dict, registry: VehicleRegistry, emit: Callable[[str, dict], None]):
        self.config = config
        self.registry = registry
        self.emit = emit
        self.junctions = {item["junction_id"]: item for item in config["junctions"]}
        self.signals = SimulatedSignalController(
            config["signal_timing_seconds"], config["normal_cycle"], emit,
            {item["junction_id"]: item.get("ambulance_direction", "north_south") for item in config["junctions"]},
        )
        self._lock = threading.RLock()
        self._routes: dict[str, dict] = {}
        self._stop = threading.Event()
        self._ticker: Optional[threading.Thread] = None

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
        points = [dict(point) for point in (payload.get("route_points") or [])]
        if not points and payload.get("origin") and payload.get("destination"):
            points = self._fallback_points(payload["origin"], payload["destination"])
        if len(points) < 2:
            raise ValueError("route_points must contain at least an origin and destination")
        requested = payload.get("junctions") or list(self.junctions)
        unknown = [junction for junction in requested if junction not in self.junctions]
        if unknown:
            raise ValueError(f"Unknown configured junction(s): {', '.join(unknown)}")
        with self._lock:
            old = self._routes.get(ambulance_id)
            if old:
                self._release_route(old, "ROUTE_REPLACED")
            route = {
                "ambulance_id": ambulance_id,
                "vehicle_number": plate,
                "junctions": requested,
                "route_points": points,
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
                        current_lat: Optional[float] = None, current_lng: Optional[float] = None) -> dict:
        with self._lock:
            route = self._routes.get(ambulance_id)
            if not route or route["status"] != "ACTIVE":
                raise KeyError(f"No active allocated route for {ambulance_id}")
            progress_percent = max(route["progress_percent"], min(100.0, float(progress_percent)))
            if current_lat is None or current_lng is None:
                current_lat, current_lng = self._interpolate(route["route_points"], progress_percent)
            route.update({
                "progress_percent": progress_percent,
                "current_lat": current_lat,
                "current_lng": current_lng,
            })
            current = {"lat": current_lat, "lng": current_lng}
            junction_count = max(1, len(route["junctions"]))
            for index, junction_id in enumerate(route["junctions"]):
                junction = self.junctions[junction_id]
                target_progress = 100.0 * (index + 1) / (junction_count + 1)
                separation = distance_m(current, junction)
                if junction_id in route["triggered_junctions"] and junction_id not in route["passed_junctions"]:
                    if progress_percent >= target_progress + 8:
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
