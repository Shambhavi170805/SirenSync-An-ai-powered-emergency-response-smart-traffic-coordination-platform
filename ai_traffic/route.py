"""
Route module: tracks ambulance GPS coordinates and triggers the 200m corridor green pre-emption.
"""

import math
from typing import Dict, List, Optional
try:
    from ai_traffic.signals import trigger_green, trigger_hold
except ImportError:
    from signals import trigger_green, trigger_hold

# Stores active ambulance data: {ambulance_id, points, junctions, progress, current_lat, current_lng}
_active_route = None


# Calculates distance in meters between two GPS coordinates using the Haversine formula
def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# Saves a new route sent by the ambulance dispatch module
def set_active_route(route_data: dict):
    global _active_route
    _active_route = route_data
    _active_route.setdefault("progress_percent", 0.0)
    print(f"[ROUTE] Route loaded for {_active_route.get('ambulance_id')}")


# Returns the currently active route
def get_active_route() -> Optional[dict]:
    return _active_route


# Updates ambulance GPS position and evaluates the 200m trigger distance
def update_ambulance_location(current_lat: float, current_lng: float, progress_percent: float, junctions_config: List[dict], trigger_distance_m: float = 200.0):
    global _active_route
    if _active_route is None:
        return

    _active_route["current_lat"] = current_lat
    _active_route["current_lng"] = current_lng
    _active_route["progress_percent"] = progress_percent
    amb_id = _active_route.get("ambulance_id", "AMBULANCE-1")

    # Find next upcoming junction along route
    for j in junctions_config:
        j_id = j.get("id")
        j_lat = j.get("lat")
        j_lng = j.get("lng")

        dist = calculate_distance_meters(current_lat, current_lng, j_lat, j_lng)

        # Within trigger distance -> turn signal GREEN
        if dist <= trigger_distance_m:
            trigger_green(j_id, amb_id, reason="ROUTE_200M_PROXIMITY")
            break
        # If very close / passing (< 30m), trigger HOLD
        elif dist < 30.0:
            trigger_hold(j_id, amb_id)
