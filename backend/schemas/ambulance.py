from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum
from backend.shared.contracts import CoordinatesContract

class AmbulanceDispatchInfo(BaseModel):
    """
    Summary of the ambulance assigned to an emergency following hospital selection.
    """
    ambulanceId: str
    vehicleNumber: str
    driverName: str
    driverContact: str
    ambulanceType: AmbulanceTypeEnum
    equipmentTags: List[str] = Field(default_factory=list)
    status: AmbulanceStatusEnum
    currentLocation: CoordinatesContract
    destinationHospitalId: Optional[str] = None
    routeProgress: float = 0.0
    estimatedDistanceKm: Optional[float] = None
    assignedAt: datetime = Field(default_factory=datetime.utcnow)

class LocationUpdateRequest(BaseModel):
    """
    Telemetry payload submitted by the ambulance/driver interface or simulator.
    """
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude between -180 and 180")
    address: Optional[str] = Field(None, description="Human readable landmark or street address")
    isSimulated: bool = Field(default=True, description="Explicitly indicates simulated coordinates for prototype")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the location update")

class RouteProgressUpdateRequest(BaseModel):
    """
    Route completion percentage update payload.
    """
    routeProgress: float = Field(..., ge=0.0, le=100.0, description="Route completion percentage (0.0 to 100.0)")
    isSimulated: bool = Field(default=True, description="Indicates simulated route progress")
    emergencyId: Optional[str] = Field(None, description="Associated emergency ID for validation")

class StatusTransitionRequest(BaseModel):
    """
    Request to transition ambulance operational lifecycle status.
    """
    status: AmbulanceStatusEnum = Field(..., description="Target lifecycle status")
    notes: Optional[str] = Field(None, description="Optional transition notes")

class AmbulanceDetailResponse(BaseModel):
    """
    Complete ambulance record representation.
    """
    id: str
    vehicleNumber: str
    driverName: str
    driverContact: str
    ambulanceType: AmbulanceTypeEnum
    equipmentTags: List[str] = Field(default_factory=list)
    status: AmbulanceStatusEnum
    currentLocation: CoordinatesContract
    assignedEmergencyId: Optional[str] = None
    destinationHospitalId: Optional[str] = None
    routeProgress: float = 0.0
    isSimulated: bool = True
    version: int = 1
    updatedAt: datetime

class TrackingSnapshotResponse(BaseModel):
    """
    Live tracking snapshot consumable by patient UI, hospital desk, and traffic coordinator.
    """
    emergencyId: str
    ambulanceId: str
    vehicleNumber: str
    driverName: str
    driverContact: str
    ambulanceType: AmbulanceTypeEnum
    status: AmbulanceStatusEnum
    currentLocation: CoordinatesContract
    destinationHospitalId: Optional[str] = None
    destinationHospitalName: Optional[str] = None
    routeProgress: float
    isSimulated: bool
    timestamp: datetime
    rerouteAlert: Optional[str] = None
