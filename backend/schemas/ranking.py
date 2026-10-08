from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from backend.models.enums import PriorityEnum, BedTypeEnum
from backend.schemas.bed import BedCategoryCount
from backend.shared.contracts import CoordinatesContract

class RankingRequest(BaseModel):
    emergencyId: str = Field(..., description="Shared Emergency ID from Intake")
    patientLocation: CoordinatesContract
    emergencyType: str = Field(..., description="Condition type, e.g. CARDIAC_ARREST, SEVERE_TRAUMA")
    priority: PriorityEnum = Field(..., description="Emergency triage priority P1 to P4")
    requiredBedType: BedTypeEnum = Field(..., description="Target bed category")
    requiredCapabilities: List[str] = Field(default_factory=list, description="Required clinical capability codes")

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
    rankedHospitals: List[RankedHospitalItem]
    weightsApplied: Dict[str, float]
    totalHospitalsEvaluated: int
    eligibleHospitalsCount: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
