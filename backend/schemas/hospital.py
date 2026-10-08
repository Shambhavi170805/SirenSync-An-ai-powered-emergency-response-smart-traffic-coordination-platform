from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class HospitalCapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    capability_code: str
    description: Optional[str] = None

class HospitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    contact_number: str
    is_active: bool
    capabilities: List[HospitalCapabilityResponse] = Field(default_factory=list)

class HospitalDetailResponse(HospitalResponse):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
    total_beds: int = 0
    available_beds: int = 0
