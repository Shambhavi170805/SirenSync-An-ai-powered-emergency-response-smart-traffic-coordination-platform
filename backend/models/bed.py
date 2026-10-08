from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base
from backend.models.enums import BedTypeEnum, BedStatusEnum

class Bed(Base):
    __tablename__ = "beds"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    hospital_id: Mapped[str] = mapped_column(String(64), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    bed_number: Mapped[str] = mapped_column(String(50), nullable=False)
    bed_type: Mapped[BedTypeEnum] = mapped_column(SQLEnum(BedTypeEnum), nullable=False, index=True)
    status: Mapped[BedStatusEnum] = mapped_column(SQLEnum(BedStatusEnum), default=BedStatusEnum.AVAILABLE, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="beds")
    reservations: Mapped[list["BedReservation"]] = relationship("BedReservation", back_populates="bed")
