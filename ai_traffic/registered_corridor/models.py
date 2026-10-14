"""API models shared with the ambulance route and tracking producer."""

from typing import List, Optional
from pydantic import BaseModel, Field, root_validator


class RoutePoint(BaseModel):
    lat: float
    lng: float


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

    @root_validator(pre=True)
    def accept_shared_backend_names(cls, values):
        # Nidhi's API responses use camelCase; the AI-traffic contract uses snake_case.
        values = dict(values or {})
        for local, shared in (("ambulance_id", "ambulanceId"), ("vehicle_number", "vehicleNumber"), ("emergency_severity", "emergencySeverity"), ("route_points", "routePoints")):
            if local not in values and shared in values:
                values[local] = values[shared]
        return values


class RouteProgress(BaseModel):
    ambulance_id: str
    progress_percent: float = Field(ge=0, le=100)
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None

    @root_validator(pre=True)
    def accept_shared_backend_names(cls, values):
        values = dict(values or {})
        for local, shared in (("ambulance_id", "ambulanceId"), ("progress_percent", "routeProgress"), ("current_lat", "latitude"), ("current_lng", "longitude")):
            if local not in values and shared in values:
                values[local] = values[shared]
        return values
