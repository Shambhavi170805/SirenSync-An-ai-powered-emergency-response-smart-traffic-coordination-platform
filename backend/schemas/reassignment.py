from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from backend.models.enums import PriorityEnum, BedTypeEnum
from backend.schemas.reservation import BedReservationDetail
from backend.shared.contracts import RerouteEventContract, CoordinatesContract

class ReassignmentEvaluationRequest(BaseModel):
    displacingEmergencyId: str = Field(..., description="ID of newly incoming emergency")
    displacingPriority: PriorityEnum = Field(..., description="Priority of new emergency, e.g. P1_CRITICAL")
    requiredBedType: BedTypeEnum = Field(..., description="Bed type needed")
    targetHospitalId: str = Field(..., description="Target hospital where bed contention exists")
    patientLocation: CoordinatesContract

class ReassignmentEvaluationResponse(BaseModel):
    decision: str = Field(..., description="'REASSIGNMENT_APPROVED' or 'REASSIGNMENT_REJECTED'")
    reason: str
    thresholdPercent: float = 40.0
    displacedEmergencyId: Optional[str] = None
    routeProgress: Optional[float] = None
    displacingReservation: Optional[BedReservationDetail] = None
    rerouteEvent: Optional[RerouteEventContract] = None
    nextBestHospital: Optional[Dict[str, Any]] = None

class ReassignmentAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    eventId: str
    displacedEmergencyId: str
    displacingEmergencyId: str
    displacedPriority: PriorityEnum
    displacingPriority: PriorityEnum
    previousHospitalId: str
    previousBedId: str
    newHospitalId: Optional[str]
    newBedId: Optional[str]
    routeProgress: float
    threshold: float
    decision: str
    reason: str
    createdAt: datetime
