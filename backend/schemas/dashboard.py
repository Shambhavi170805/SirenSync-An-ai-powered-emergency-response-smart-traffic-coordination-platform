from typing import List
from datetime import datetime
from pydantic import BaseModel, Field
from backend.schemas.hospital import HospitalDetailResponse
from backend.schemas.bed import HospitalBedSummaryResponse
from backend.schemas.queue import HospitalQueueResponse

class HospitalDashboardOverviewResponse(BaseModel):
    hospital: HospitalDetailResponse
    bedSummary: HospitalBedSummaryResponse
    queue: List[HospitalQueueResponse] = Field(default_factory=list)
    activeReservationsCount: int = 0
    totalQueueCount: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
