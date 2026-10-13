"""
Ambulance Route and Corridor Coordinator.
Processes incoming GPS and progress updates from the upstream ambulance coordination module.
Calculates junction proximity via Haversine geometry and triggers pre-emptive green signal
corridors along the ambulance travel path.
"""

import math
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel

from ai_traffic.core.config import JunctionConfig, SignalsConfig
from ai_traffic.core.database import get_db
from ai_traffic.core.logger import logger
from ai_traffic.signals.state_machine import JunctionStateMachine


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in meters.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


class RouteManager:
    """
    Tracks emergency vehicles along defined transit corridors.
    """

    def __init__(
        self,
        signals_config: SignalsConfig,
        junction_configs: List[JunctionConfig],
        state_machine: JunctionStateMachine,
        on_event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        self.config = signals_config
        self.junctions = {j.junction_id: j for j in junction_configs}
        self.state_machine = state_machine
        self.on_event = on_event_callback
        self.db = get_db()

        self._active_routes: Dict[str, Dict[str, Any]] = {}
        self._preempted_junctions: Dict[str, str] = {}  # junction_id -> ambulance_id

    def ingest_route(
        self,
        ambulance_id: str,
        route_points: List[Dict[str, float]],
        junctions_on_route: List[str],
        progress_percent: float = 0.0,
        emergency_severity: str = "CRITICAL"
    ) -> Dict[str, Any]:
        """
        Stores and activates a new transit corridor route.
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        route_data = {
            "ambulance_id": ambulance_id,
            "route_points": route_points,
            "junctions_on_route": junctions_on_route,
            "progress_percent": progress_percent,
            "emergency_severity": emergency_severity,
            "updated_at": now_ts,
            "status": "ACTIVE"
        }
        self._active_routes[ambulance_id] = route_data

        logger.info(
            f"[ROUTE INGEST] Registered route for {ambulance_id} with {len(route_points)} points "
            f"across junctions: {junctions_on_route}"
        )

        # Check proximity right away
        self._evaluate_corridor(ambulance_id)
        return route_data

    def update_progress(
        self,
        ambulance_id: str,
        progress_percent: float,
        current_lat: Optional[float] = None,
        current_lng: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        route = self._active_routes.get(ambulance_id)
        if not route:
            logger.warning(f"[ROUTE MGR] Cannot update progress for unknown ambulance '{ambulance_id}'")
            return None

        route["progress_percent"] = max(0.0, min(100.0, progress_percent))
        route["updated_at"] = datetime.now(timezone.utc).isoformat()

        # If explicit coordinates not supplied, interpolate from progress percent along points
        points = route["route_points"]
        if (current_lat is None or current_lng is None) and points:
            idx = int((route["progress_percent"] / 100.0) * (len(points) - 1))
            current_lat = points[idx]["lat"]
            current_lng = points[idx]["lng"]

        route["current_lat"] = current_lat
        route["current_lng"] = current_lng

        if route["progress_percent"] >= 100.0:
            route["status"] = "COMPLETED"
            # Release all active signals for this ambulance
            for j_id in route["junctions_on_route"]:
                if self._preempted_junctions.get(j_id) == ambulance_id:
                    self.state_machine.trigger_clearance(j_id, ambulance_id, reason="ROUTE_COMPLETED")
                    self._preempted_junctions.pop(j_id, None)

        # Re-evaluate upcoming junctions
        next_junction = self._evaluate_corridor(ambulance_id)

        # Emit ROUTE_UPDATED event
        now_ts = datetime.now(timezone.utc).isoformat()
        event_payload = {
            "ambulance_id": ambulance_id,
            "progress_percent": route["progress_percent"],
            "current_lat": current_lat,
            "current_lng": current_lng,
            "next_junction_id": next_junction,
            "status": route["status"],
            "timestamp": now_ts
        }
        self.db.insert_event("ROUTE_UPDATED", event_payload, timestamp=now_ts)
        if self.on_event:
            self.on_event("ROUTE_UPDATED", event_payload)

        return route

    def _evaluate_corridor(self, ambulance_id: str) -> Optional[str]:
        route = self._active_routes.get(ambulance_id)
        if not route or route["status"] != "ACTIVE":
            return None

        cur_lat = route.get("current_lat")
        cur_lng = route.get("current_lng")
        if cur_lat is None or cur_lng is None:
            points = route["route_points"]
            if points:
                cur_lat = points[0]["lat"]
                cur_lng = points[0]["lng"]
            else:
                return None

        closest_upcoming_junction: Optional[str] = None
        min_upcoming_dist = float("inf")

        # Evaluate distance to each junction on this route
        for j_id in route["junctions_on_route"]:
            j_cfg = self.junctions.get(j_id)
            if not j_cfg:
                continue

            dist = haversine_distance_meters(cur_lat, cur_lng, j_cfg.lat, j_cfg.lng)
            # Assume average ambulance speed in city transit ~40 km/h (11.1 m/s)
            eta_seconds = dist / 11.1

            # Proximity pre-emption threshold check
            if dist <= self.config.preemption_distance_meters or eta_seconds <= self.config.preemption_lead_time_seconds:
                # Trigger green corridor
                if self._preempted_junctions.get(j_id) != ambulance_id:
                    logger.info(
                        f"[CORRIDOR PROXIMITY] Ambulance {ambulance_id} is {dist:.1f}m (ETA {eta_seconds:.1f}s) "
                        f"from Junction {j_id}. Triggering PRE-EMPTIVE GREEN!"
                    )
                    success = self.state_machine.trigger_preemption(
                        junction_id=j_id,
                        ambulance_id=ambulance_id,
                        reason="ROUTE_PROXIMITY_PREEMPTION",
                        severity=route.get("emergency_severity", "CRITICAL"),
                        eta_seconds=eta_seconds,
                        distance_meters=dist
                    )
                    if success:
                        self._preempted_junctions[j_id] = ambulance_id

            if dist < min_upcoming_dist:
                min_upcoming_dist = dist
                closest_upcoming_junction = j_id

        return closest_upcoming_junction

    def get_route(self, ambulance_id: str) -> Optional[Dict[str, Any]]:
        return self._active_routes.get(ambulance_id)

    def get_all_routes(self) -> List[Dict[str, Any]]:
        return list(self._active_routes.values())
