"""
Shared Emergency Domain Entity
This entity represents the common emergency record created by Shambhavi's
Patient Experience & Intake subsystem and consumed across SirenSync subsystems.
Samriddhi's subsystem consumes this entity for ranking, bed locking, and incoming queue tracking.
"""
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base
from backend.models.enums import PriorityEnum, BedTypeEnum

class Emergency(Base):
    __tablename__ = "emergencies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True) # Shared emergency_id
    patient_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    emergency_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. CARDIAC, TRAUMA, RESPIRATORY
    priority: Mapped[PriorityEnum] = mapped_column(SQLEnum(PriorityEnum), nullable=False, index=True)
    patient_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    patient_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    patient_address: Mapped[str] = mapped_column(String(500), nullable=True)
    required_bed_type: Mapped[BedTypeEnum] = mapped_column(SQLEnum(BedTypeEnum), nullable=False)
    
    # Coordinating hospital set upon patient selection
    selected_hospital_id: Mapped[str] = mapped_column(String(64), ForeignKey("hospitals.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    reservations: Mapped[list["BedReservation"]] = relationship("BedReservation", back_populates="emergency")
    queue_item: Mapped["HospitalQueueItem"] = relationship("HospitalQueueItem", back_populates="emergency", uselist=False)
