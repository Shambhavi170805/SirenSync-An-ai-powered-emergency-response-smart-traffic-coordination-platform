"""
SirenSync Cross-Module Integration Contracts & Event Schemas
This file defines the stable interface between:
- Shambhavi (Patient Intake / Selection)
- Samriddhi (Hospital Intelligence & Bed Management)
- Nidhi (Ambulance Coordination & Real-Time Tracking)
- Ishita (AI Traffic & Green Corridor)
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from backend.models.enums import PriorityEnum, BedTypeEnum

# Standard Event Type Identifiers
EVENT_BED_REASSIGNMENT_REROUTE = "BED_REASSIGNMENT_REROUTE"
EVENT_BED_RESERVED = "BED_RESERVED"
EVENT_AMBULANCE_DISPATCH_TRIGGERED = "AMBULANCE_DISPATCH_TRIGGERED"

class CoordinatesContract(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    address: Optional[str] = Field(None, description="Human readable landmark or address")

class EmergencySharedContract(BaseModel):
    """
    Emergency record payload originated by Shambhavi's Intake Subsystem
    and consumed by Samriddhi's Hospital Intelligence Subsystem.
    """
    emergency_id: str
    patient_id: str
    emergency_type: str
    priority: PriorityEnum
    patient_location: CoordinatesContract
    required_bed_type: BedTypeEnum
    required_capabilities: List[str] = Field(default_factory=list)

class RouteProgressUpdateContract(BaseModel):
    """
    Ambulance tracking progress payload reported by Nidhi's Subsystem
    and consumed by Samriddhi's Bed Reassignment Policy Engine.
    """
    ambulance_id: str
    emergency_id: str
    route_progress: float = Field(..., ge=0.0, le=100.0, description="Route completion percentage (0.0 to 100.0)")
    current_location: Optional[CoordinatesContract] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class RerouteEventContract(BaseModel):
    """
    Machine-readable rerouting event emitted by Samriddhi's Subsystem
    and consumed by Nidhi's Ambulance Coordination Subsystem.
    """
    eventType: str = Field(default=EVENT_BED_REASSIGNMENT_REROUTE)
    eventId: str
    emergencyId: str
    previousHospitalId: str
    previousBedId: str
    newHospitalId: Optional[str] = None
    newBedId: Optional[str] = None
    displacingEmergencyId: str
    displacingPriority: PriorityEnum
    displacedPriority: PriorityEnum
    reason: str = "HIGHER_PRIORITY_EMERGENCY"
    routeProgress: float
    threshold: float = 40.0
    status: str = "REROUTE_REQUIRED"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
