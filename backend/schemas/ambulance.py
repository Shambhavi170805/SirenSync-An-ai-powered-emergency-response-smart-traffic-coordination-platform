import math
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasChoices, field_validator
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum
from backend.shared.contracts import CoordinatesContract

class AmbulanceDispatchInfo(BaseModel):
    """
    Summary of the ambulance assigned to an emergency following hospital selection.
    """
    model_config = ConfigDict(populate_by_name=True)

    ambulanceId: str = Field(..., validation_alias=AliasChoices("ambulanceId", "ambulance_id", "id"))
    vehicleNumber: str = Field(..., validation_alias=AliasChoices("vehicleNumber", "vehicle_number"))
    driverName: str = Field(..., validation_alias=AliasChoices("driverName", "driver_name"))
    driverContact: str = Field(..., validation_alias=AliasChoices("driverContact", "driver_contact"))
    ambulanceType: AmbulanceTypeEnum = Field(..., validation_alias=AliasChoices("ambulanceType", "ambulance_type"))
    equipmentTags: List[str] = Field(default_factory=list, validation_alias=AliasChoices("equipmentTags", "equipment_tags"))
    status: AmbulanceStatusEnum
    currentLocation: CoordinatesContract = Field(..., validation_alias=AliasChoices("currentLocation", "current_location"))
    destinationHospitalId: Optional[str] = Field(None, validation_alias=AliasChoices("destinationHospitalId", "destination_hospital_id"))
    routeProgress: float = Field(0.0, validation_alias=AliasChoices("routeProgress", "route_progress"))
    estimatedDistanceKm: Optional[float] = Field(None, validation_alias=AliasChoices("estimatedDistanceKm", "estimated_distance_km"))
    assignedAt: datetime = Field(default_factory=datetime.utcnow, validation_alias=AliasChoices("assignedAt", "assigned_at"))

class LocationUpdateRequest(BaseModel):
    """
    Telemetry payload submitted by the ambulance/driver interface or simulator.
    """
    model_config = ConfigDict(populate_by_name=True)

    latitude: float = Field(..., description="WGS84 Latitude between -90 and 90")
    longitude: float = Field(..., description="WGS84 Longitude between -180 and 180")
    address: Optional[str] = Field(None, description="Human readable landmark or street address")
    isSimulated: bool = Field(default=True, validation_alias=AliasChoices("isSimulated", "is_simulated"), description="Explicitly indicates simulated coordinates for prototype")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the location update")
    routeProgress: Optional[float] = Field(None, ge=0.0, le=100.0, validation_alias=AliasChoices("routeProgress", "route_progress"), description="GPS-derived route progress; never manually required")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Latitude must be a finite number.")
        if v < -90.0 or v > 90.0:
            raise ValueError("Latitude must be between -90 and 90 degrees.")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Longitude must be a finite number.")
        if v < -180.0 or v > 180.0:
            raise ValueError("Longitude must be between -180 and 180 degrees.")
        return v

class RouteProgressUpdateRequest(BaseModel):
    """
    Route completion percentage update payload.
    """
    model_config = ConfigDict(populate_by_name=True)

    routeProgress: float = Field(..., validation_alias=AliasChoices("routeProgress", "route_progress"), description="Route completion percentage (0.0 to 100.0)")
    isSimulated: bool = Field(default=True, validation_alias=AliasChoices("isSimulated", "is_simulated"), description="Indicates simulated route progress")
    emergencyId: Optional[str] = Field(None, validation_alias=AliasChoices("emergencyId", "emergency_id"), description="Associated emergency ID for validation")

    @field_validator("routeProgress")
    @classmethod
    def validate_route_progress(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Route progress must be a finite number.")
        if v < 0.0 or v > 100.0:
            raise ValueError("Route progress must be between 0.0 and 100.0.")
        return v

class StatusTransitionRequest(BaseModel):
    """
    Request to transition ambulance operational lifecycle status.
    """
    model_config = ConfigDict(populate_by_name=True)

    status: AmbulanceStatusEnum = Field(..., description="Target lifecycle status")
    notes: Optional[str] = Field(None, description="Optional transition notes")

class AmbulanceDetailResponse(BaseModel):
    """
    Complete ambulance record representation.
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    vehicleNumber: str = Field(..., validation_alias=AliasChoices("vehicleNumber", "vehicle_number"))
    driverName: str = Field(..., validation_alias=AliasChoices("driverName", "driver_name"))
    driverContact: str = Field(..., validation_alias=AliasChoices("driverContact", "driver_contact"))
    ambulanceType: AmbulanceTypeEnum = Field(..., validation_alias=AliasChoices("ambulanceType", "ambulance_type"))
    equipmentTags: List[str] = Field(default_factory=list, validation_alias=AliasChoices("equipmentTags", "equipment_tags"))
    status: AmbulanceStatusEnum
    currentLocation: CoordinatesContract = Field(..., validation_alias=AliasChoices("currentLocation", "current_location"))
    assignedEmergencyId: Optional[str] = Field(None, validation_alias=AliasChoices("assignedEmergencyId", "assigned_emergency_id"))
    destinationHospitalId: Optional[str] = Field(None, validation_alias=AliasChoices("destinationHospitalId", "destination_hospital_id"))
    routeProgress: float = Field(0.0, validation_alias=AliasChoices("routeProgress", "route_progress"))
    isSimulated: bool = Field(True, validation_alias=AliasChoices("isSimulated", "is_simulated"))
    version: int = 1
    updatedAt: datetime = Field(..., validation_alias=AliasChoices("updatedAt", "updated_at"))

class TrackingSnapshotResponse(BaseModel):
    """
    Live tracking snapshot consumable by patient UI, hospital desk, and traffic coordinator.
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    emergencyId: str = Field(..., validation_alias=AliasChoices("emergencyId", "emergency_id"))
    ambulanceId: str = Field(..., validation_alias=AliasChoices("ambulanceId", "ambulance_id"))
    vehicleNumber: str = Field(..., validation_alias=AliasChoices("vehicleNumber", "vehicle_number"))
    driverName: str = Field(..., validation_alias=AliasChoices("driverName", "driver_name"))
    driverContact: str = Field(..., validation_alias=AliasChoices("driverContact", "driver_contact"))
    ambulanceType: AmbulanceTypeEnum = Field(..., validation_alias=AliasChoices("ambulanceType", "ambulance_type"))
    status: AmbulanceStatusEnum
    currentLocation: CoordinatesContract = Field(..., validation_alias=AliasChoices("currentLocation", "current_location"))
    destinationHospitalId: Optional[str] = Field(None, validation_alias=AliasChoices("destinationHospitalId", "destination_hospital_id"))
    destinationHospitalName: Optional[str] = Field(None, validation_alias=AliasChoices("destinationHospitalName", "destination_hospital_name"))
    routeProgress: float = Field(0.0, validation_alias=AliasChoices("routeProgress", "route_progress"))
    isSimulated: bool = Field(True, validation_alias=AliasChoices("isSimulated", "is_simulated"))
    timestamp: datetime
    rerouteAlert: Optional[str] = Field(None, validation_alias=AliasChoices("rerouteAlert", "reroute_alert"))
