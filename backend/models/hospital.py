from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base

class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    contact_number: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    capabilities: Mapped[list["HospitalCapability"]] = relationship(
        "HospitalCapability", back_populates="hospital", cascade="all, delete-orphan"
    )
    beds: Mapped[list["Bed"]] = relationship(
        "Bed", back_populates="hospital", cascade="all, delete-orphan"
    )
    reservations: Mapped[list["BedReservation"]] = relationship(
        "BedReservation", back_populates="hospital"
    )
    queue_items: Mapped[list["HospitalQueueItem"]] = relationship(
        "HospitalQueueItem", back_populates="hospital", cascade="all, delete-orphan"
    )

class HospitalCapability(Base):
    __tablename__ = "hospital_capabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[str] = mapped_column(String(64), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    capability_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)

    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="capabilities")
