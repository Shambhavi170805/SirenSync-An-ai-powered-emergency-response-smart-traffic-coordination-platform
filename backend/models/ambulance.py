from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum

class Ambulance(Base):
    __tablename__ = "ambulances"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    vehicle_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    driver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    driver_contact: Mapped[str] = mapped_column(String(50), nullable=False)
    ambulance_type: Mapped[AmbulanceTypeEnum] = mapped_column(
        SQLEnum(AmbulanceTypeEnum), default=AmbulanceTypeEnum.ALS, nullable=False, index=True
    )
    equipment_tags: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[AmbulanceStatusEnum] = mapped_column(
        SQLEnum(AmbulanceStatusEnum), default=AmbulanceStatusEnum.AVAILABLE, nullable=False, index=True
    )
    current_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    current_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    current_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Active dispatch associations
    assigned_emergency_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("emergencies.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )
    destination_hospital_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    route_progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    emergency: Mapped[Optional["Emergency"]] = relationship("Emergency", foreign_keys=[assigned_emergency_id])
    destination_hospital: Mapped[Optional["Hospital"]] = relationship("Hospital", foreign_keys=[destination_hospital_id])
