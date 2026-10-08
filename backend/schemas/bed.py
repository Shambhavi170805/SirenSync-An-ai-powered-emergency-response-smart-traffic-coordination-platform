from typing import Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.models.enums import BedTypeEnum, BedStatusEnum

class BedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    hospital_id: str
    bed_number: str
    bed_type: BedTypeEnum
    status: BedStatusEnum
    department: str
    updated_at: datetime

class BedCategoryCount(BaseModel):
    available: int
    reserved: int
    occupied: int
    total: int

class HospitalBedSummaryResponse(BaseModel):
    hospital_id: str
    total_beds: int
    available_beds: int
    reserved_beds: int
    occupied_beds: int
    by_category: Dict[str, BedCategoryCount]

class BedStatusUpdateRequest(BaseModel):
    status: BedStatusEnum

