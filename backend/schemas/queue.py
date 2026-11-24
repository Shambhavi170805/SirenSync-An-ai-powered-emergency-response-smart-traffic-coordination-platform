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
    patient_id: Optional[str] = None
    emergency_type: Optional[str] = None
    symptoms: Optional[str] = None
    patient_address: Optional[str] = None
    ambulance_id: Optional[str] = None
    ambulance_vehicle_number: Optional[str] = None
    ambulance_driver_name: Optional[str] = None
    ambulance_status: Optional[str] = None
    ambulance_is_simulated: Optional[bool] = None
