from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base
from backend.models.enums import ReservationStatusEnum

class BedReservation(Base):
    __tablename__ = "bed_reservations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    emergency_id: Mapped[str] = mapped_column(String(64), ForeignKey("emergencies.id", ondelete="CASCADE"), nullable=False, index=True)
    hospital_id: Mapped[str] = mapped_column(String(64), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    bed_id: Mapped[str] = mapped_column(String(64), ForeignKey("beds.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[ReservationStatusEnum] = mapped_column(
        SQLEnum(ReservationStatusEnum), default=ReservationStatusEnum.RESERVED, nullable=False, index=True
    )
    reserved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    released_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    reassigned_to_emergency_id: Mapped[str] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    emergency: Mapped["Emergency"] = relationship("Emergency", back_populates="reservations")
    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="reservations")
    bed: Mapped["Bed"] = relationship("Bed", back_populates="reservations")
