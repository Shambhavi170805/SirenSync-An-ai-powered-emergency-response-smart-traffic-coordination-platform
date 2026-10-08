from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from backend.models.enums import BedTypeEnum, ReservationStatusEnum
from backend.shared.contracts import CoordinatesContract

class HospitalSelectionRequest(BaseModel):
    selectedHospitalId: str = Field(..., description="Hospital ID chosen by the patient in Shambhavi's UI")
    requiredBedType: BedTypeEnum = Field(..., description="Bed category needed for this emergency")
    patientId: Optional[str] = Field(None, description="Patient ID if already registered")
    patientLocation: Optional[CoordinatesContract] = None

class BedReservationDetail(BaseModel):
    reservationId: str
    bedId: str
    bedNumber: str
    bedType: BedTypeEnum
    status: ReservationStatusEnum
    reservedAt: datetime

class CoordinatingHospitalInfo(BaseModel):
    hospitalId: str
    hospitalName: str
    contactNumber: str
    address: str
    dispatchStatus: str = "AMBULANCE_COORDINATION_INITIATED"

class HospitalSelectionResponse(BaseModel):
    status: str = "SUCCESS"
    emergencyId: str
    hospitalId: str
    reservation: BedReservationDetail
    coordinatingHospital: CoordinatingHospitalInfo
    message: str = "Bed reserved securely. Hospital is now the coordinating authority."
