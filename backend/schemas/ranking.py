from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from backend.models.enums import PriorityEnum, BedTypeEnum
from backend.schemas.bed import BedCategoryCount
from backend.shared.contracts import CoordinatesContract

class RankingRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    emergencyId: str = Field(..., validation_alias=AliasChoices("emergencyId", "emergency_id"), description="Shared Emergency ID from Intake")
    patientLocation: CoordinatesContract = Field(..., validation_alias=AliasChoices("patientLocation", "patient_location"))
    emergencyType: str = Field(..., validation_alias=AliasChoices("emergencyType", "emergency_type"), description="Condition type, e.g. CARDIAC_ARREST, SEVERE_TRAUMA")
    priority: PriorityEnum = Field(..., validation_alias=AliasChoices("priority", "priority"), description="Emergency triage priority P1 to P4")
    requiredBedType: BedTypeEnum = Field(..., validation_alias=AliasChoices("requiredBedType", "required_bed_type"), description="Target bed category")
    requiredCapabilities: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("requiredCapabilities", "required_capabilities"),
        description="Required clinical capability codes"
    )

class RankingBreakdown(BaseModel):
    distanceKm: float
    distanceScore: float
    capabilityMatchScore: float
    matchedCapabilities: List[str]
    missingCapabilities: List[str]
    trafficCongestionFactor: float
    trafficScore: float
    bedAvailabilityScore: float
    availableBedsCount: int
    explanation: str

class RankedHospitalItem(BaseModel):
    hospitalId: str
    name: str
    location: CoordinatesContract
    contactNumber: str
    compositeScore: float
    rank: int
    isEligible: bool
    breakdown: RankingBreakdown
    bedSummary: Dict[str, BedCategoryCount]

class RankedHospitalsResponse(BaseModel):
    emergencyId: str
    requiredCapabilities: List[str] = Field(default_factory=list, description="Echo of requested capabilities evaluated")
    rankedHospitals: List[RankedHospitalItem]
    weightsApplied: Dict[str, float]
    totalHospitalsEvaluated: int
    eligibleHospitalsCount: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
