from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.models.enums import PriorityEnum, QueueStatusEnum

class HospitalQueueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    hospital_id: str
    emergency_id: str
    priority: PriorityEnum
    status: QueueStatusEnum
    route_progress: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
