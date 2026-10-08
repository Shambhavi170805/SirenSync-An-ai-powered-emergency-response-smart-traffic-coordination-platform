from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from backend.models.enums import PriorityEnum, BedTypeEnum
from backend.schemas.reservation import BedReservationDetail
from backend.shared.contracts import RerouteEventContract, CoordinatesContract

class ReassignmentEvaluationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    displacingEmergencyId: str = Field(..., validation_alias=AliasChoices("displacingEmergencyId", "displacing_emergency_id"), description="ID of newly incoming emergency")
    displacingPriority: PriorityEnum = Field(..., validation_alias=AliasChoices("displacingPriority", "displacing_priority"), description="Priority of new emergency, e.g. P1_CRITICAL")
    requiredBedType: BedTypeEnum = Field(..., validation_alias=AliasChoices("requiredBedType", "required_bed_type"), description="Bed type needed")
    targetHospitalId: str = Field(..., validation_alias=AliasChoices("targetHospitalId", "target_hospital_id"), description="Target hospital where bed contention exists")
    patientLocation: CoordinatesContract = Field(..., validation_alias=AliasChoices("patientLocation", "patient_location"))
    simulatedRouteProgress: Optional[float] = Field(
        None,
        validation_alias=AliasChoices("simulatedRouteProgress", "simulated_route_progress", "routeProgress", "route_progress"),
        description="Optional route progress percentage (0.0 to 100.0) for evaluator testing"
    )

class ReassignmentEvaluationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    decision: str = Field(..., description="'REASSIGNMENT_APPROVED' or 'REASSIGNMENT_REJECTED'")
    reason: str
    thresholdPercent: float = 40.0
    displacedEmergencyId: Optional[str] = None
    routeProgress: Optional[float] = None
    displacedReservationStatus: Optional[str] = None
    displacingReservation: Optional[BedReservationDetail] = None
    rerouteEvent: Optional[RerouteEventContract] = None
    nextBestHospital: Optional[Dict[str, Any]] = None
    rerouteRequired: bool = False
    scenarioName: Optional[str] = None

class ReassignmentAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: str
    eventId: str = Field(..., validation_alias=AliasChoices("eventId", "event_id"))
    displacedEmergencyId: str = Field(..., validation_alias=AliasChoices("displacedEmergencyId", "displaced_emergency_id"))
    displacingEmergencyId: str = Field(..., validation_alias=AliasChoices("displacingEmergencyId", "displacing_emergency_id"))
    displacedPriority: PriorityEnum = Field(..., validation_alias=AliasChoices("displacedPriority", "displaced_priority"))
    displacingPriority: PriorityEnum = Field(..., validation_alias=AliasChoices("displacingPriority", "displacing_priority"))
    previousHospitalId: str = Field(..., validation_alias=AliasChoices("previousHospitalId", "previous_hospital_id"))
    previousBedId: str = Field(..., validation_alias=AliasChoices("previousBedId", "previous_bed_id"))
    newHospitalId: Optional[str] = Field(None, validation_alias=AliasChoices("newHospitalId", "new_hospital_id"))
    newBedId: Optional[str] = Field(None, validation_alias=AliasChoices("newBedId", "new_bed_id"))
    routeProgress: float = Field(..., validation_alias=AliasChoices("routeProgress", "route_progress"))
    threshold: float = 40.0
    decision: str
    reason: str
    createdAt: datetime = Field(..., validation_alias=AliasChoices("createdAt", "created_at"))
