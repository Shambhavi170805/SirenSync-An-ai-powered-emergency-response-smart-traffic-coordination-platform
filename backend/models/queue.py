from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base
from backend.models.enums import PriorityEnum, QueueStatusEnum

class HospitalQueueItem(Base):
    __tablename__ = "hospital_queue_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    hospital_id: Mapped[str] = mapped_column(String(64), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    emergency_id: Mapped[str] = mapped_column(String(64), ForeignKey("emergencies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    priority: Mapped[PriorityEnum] = mapped_column(SQLEnum(PriorityEnum), nullable=False, index=True)
    status: Mapped[QueueStatusEnum] = mapped_column(
        SQLEnum(QueueStatusEnum), default=QueueStatusEnum.COORDINATING, nullable=False, index=True
    )
    route_progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="queue_items")
    emergency: Mapped["Emergency"] = relationship("Emergency", back_populates="queue_item")
