"""API models shared with the ambulance route and tracking producer."""

from typing import List, Optional
from pydantic import BaseModel, Field, root_validator


class RoutePoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

    @root_validator(pre=True)
    def accept_coordinate_aliases(cls, values):
        values = dict(values or {})
        if "lat" not in values and "latitude" in values:
            values["lat"] = values["latitude"]
        if "lng" not in values and "longitude" in values:
            values["lng"] = values["longitude"]
        return values


class PatientLocation(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @root_validator(pre=True)
    def accept_short_coordinate_names(cls, values):
        values = dict(values or {})
        if "latitude" not in values and "lat" in values:
            values["latitude"] = values["lat"]
        if "longitude" not in values and "lng" in values:
            values["longitude"] = values["lng"]
        return values


class RoutePlanRequest(BaseModel):
    emergency_id: Optional[str] = None
    hospital_id: str
    patient_location: PatientLocation
    # When Shambhavi has a selected road route, send its ordered WGS84 points.
    # The traffic module map-matches these points and discovers intersections
    # along that same route instead of calculating a different route.
    route_points: Optional[List[RoutePoint]] = Field(default=None, min_items=2, max_items=1000)

    @root_validator(pre=True)
    def accept_shared_backend_names(cls, values):
        values = dict(values or {})
        for local, shared in (("emergency_id", "emergencyId"), ("hospital_id", "hospitalId"), ("patient_location", "patientLocation")):
            if local not in values and shared in values:
                values[local] = values[shared]
        if "route_points" not in values:
            route = values.get("selectedRoute") or values.get("route") or {}
            if not isinstance(route, dict):
                route = {}
            route_geometry = (values.get("routeGeometry") or values.get("route_geometry")
                              or route.get("routeGeometry") or route.get("geometry"))
            points = (values.get("routePoints") or route.get("routePoints") or route.get("route_points")
                      or (route_geometry.get("coordinates") if isinstance(route_geometry, dict) else None))
            if isinstance(points, dict):
                points = points.get("coordinates")
            # GeoJSON coordinate order is [longitude, latitude].
            if points and isinstance(points[0], (list, tuple)):
                points = [{"lng": point[0], "lat": point[1]} for point in points]
            if points is not None:
                values["route_points"] = points
        return values


class DemoStartRequest(BaseModel):
    route_plan_id: str
    route_option: int = Field(default=0, ge=0, le=2)

    @root_validator(pre=True)
    def accept_shared_backend_names(cls, values):
        values = dict(values or {})
        if "route_plan_id" not in values and "routePlanId" in values:
            values["route_plan_id"] = values["routePlanId"]
        if "route_option" not in values and "routeOption" in values:
            values["route_option"] = values["routeOption"]
        return values


class RouteAllocation(BaseModel):
    ambulance_id: str
    # Nidhi's ambulance model names this property `vehicle_number`.
    vehicle_number: str
    junctions: List[str] = Field(default_factory=list)
    route_points: Optional[List[RoutePoint]] = Field(default=None, min_items=2)
    # Matches the optional origin/destination contract in the shared AI-traffic API.
    origin: Optional[str] = None
    destination: Optional[str] = None
    emergency_severity: str = "CRITICAL"
    # Nidhi's tracking API scopes live telemetry by emergency ID.
    emergency_id: Optional[str] = None
    is_simulated: Optional[bool] = None
    route_plan_id: Optional[str] = None
    route_option: int = Field(default=0, ge=0, le=2)

    @root_validator(pre=True)
    def accept_shared_backend_names(cls, values):
        # Nidhi's API responses use camelCase; the AI-traffic contract uses snake_case.
        values = dict(values or {})
        for local, shared in (("ambulance_id", "ambulanceId"), ("vehicle_number", "vehicleNumber"), ("emergency_severity", "emergencySeverity"), ("route_points", "routePoints"), ("emergency_id", "emergencyId"), ("is_simulated", "isSimulated"), ("route_plan_id", "routePlanId"), ("route_option", "routeOption")):
            if local not in values and shared in values:
                values[local] = values[shared]
        return values


class RouteProgress(BaseModel):
    ambulance_id: str
    progress_percent: float = Field(ge=0, le=100)
    current_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    current_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    is_simulated: Optional[bool] = None

    @root_validator(pre=True)
    def accept_shared_backend_names(cls, values):
        values = dict(values or {})
        for local, shared in (("ambulance_id", "ambulanceId"), ("progress_percent", "routeProgress"), ("current_lat", "latitude"), ("current_lng", "longitude"), ("is_simulated", "isSimulated")):
            if local not in values and shared in values:
                values[local] = values[shared]
        return values
