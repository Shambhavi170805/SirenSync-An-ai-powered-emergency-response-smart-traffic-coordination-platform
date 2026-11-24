from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from backend.models.enums import PriorityEnum, BedTypeEnum
from backend.shared.contracts import CoordinatesContract

class EmergencyCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    emergencyId: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("emergencyId", "emergency_id", "id"),
        description="Shared cross-module emergency unique identifier (generated if omitted)"
    )
    patientId: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("patientId", "patient_id"),
        description="Patient identifier from Shambhavi's intake screen"
    )
    emergencyType: str = Field(
        ...,
        validation_alias=AliasChoices("emergencyType", "emergency_type"),
        description="Condition classification, e.g. CARDIAC_ARREST, SEVERE_TRAUMA"
    )
    priority: PriorityEnum = Field(
        ...,
        description="Triage clinical urgency: P1_CRITICAL, P2_EMERGENCY, P3_URGENT, P4_NON_URGENT"
    )
    patientLocation: CoordinatesContract = Field(
        ...,
        validation_alias=AliasChoices("patientLocation", "patient_location"),
        description="Patient coordinates and landmark address"
    )
    requiredBedType: BedTypeEnum = Field(
        ...,
        validation_alias=AliasChoices("requiredBedType", "required_bed_type"),
        description="Target bed category required for admission"
    )
    symptoms: Optional[str] = Field(
        None,
        description="Reported structured patient symptoms"
    )
    region: Optional[str] = Field(
        default="Dehradun",
        validation_alias=AliasChoices("region"),
        description="Operating region (default: Dehradun)"
    )
    requiredCapabilities: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("requiredCapabilities", "required_capabilities"),
        description="Required clinical capability codes"
    )

class EmergencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    emergencyId: str = Field(..., validation_alias=AliasChoices("emergencyId", "emergency_id", "id"))
    patientId: str = Field(..., validation_alias=AliasChoices("patientId", "patient_id"))
    emergencyType: str = Field(..., validation_alias=AliasChoices("emergencyType", "emergency_type"))
    priority: PriorityEnum
    patientLocation: CoordinatesContract = Field(..., validation_alias=AliasChoices("patientLocation", "patient_location"))
    requiredBedType: BedTypeEnum = Field(..., validation_alias=AliasChoices("requiredBedType", "required_bed_type"))
    symptoms: Optional[str] = None
    region: Optional[str] = Field("Dehradun", validation_alias=AliasChoices("region"))
    requiredCapabilities: List[str] = Field(default_factory=list, validation_alias=AliasChoices("requiredCapabilities", "required_capabilities"))
    selectedHospitalId: Optional[str] = Field(None, validation_alias=AliasChoices("selectedHospitalId", "selected_hospital_id"))
    createdAt: datetime = Field(..., validation_alias=AliasChoices("createdAt", "created_at"))
    updatedAt: datetime = Field(..., validation_alias=AliasChoices("updatedAt", "updated_at"))

    @classmethod
    def from_orm_model(cls, model) -> "EmergencyResponse":
        caps = getattr(model, "required_capabilities", [])
        if caps is None:
            caps = []
        elif isinstance(caps, str):
            import json
            try:
                caps = json.loads(caps)
            except Exception:
                caps = []

        return cls(
            emergencyId=model.id,
            patientId=model.patient_id,
            emergencyType=model.emergency_type,
            priority=model.priority,
            patientLocation=CoordinatesContract(
                latitude=model.patient_latitude,
                longitude=model.patient_longitude,
                address=model.patient_address
            ),
            requiredBedType=model.required_bed_type,
            symptoms=model.symptoms,
            region=getattr(model, "region", "Dehradun") or "Dehradun",
            requiredCapabilities=caps,
            selectedHospitalId=model.selected_hospital_id,
            createdAt=model.created_at,
            updatedAt=model.updated_at
        )
