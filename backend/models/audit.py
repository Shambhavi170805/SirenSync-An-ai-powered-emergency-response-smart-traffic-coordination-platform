from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base
from backend.models.enums import PriorityEnum

class ReassignmentAuditLog(Base):
    """
    Audit log for the configurable 40% route-progress prototype bed reassignment policy.
    Note: This records evaluation of the prototype system heuristic; it is not a medical protocol.
    """
    __tablename__ = "reassignment_audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    displaced_emergency_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    displacing_emergency_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    displaced_priority: Mapped[PriorityEnum] = mapped_column(SQLEnum(PriorityEnum), nullable=False)
    displacing_priority: Mapped[PriorityEnum] = mapped_column(SQLEnum(PriorityEnum), nullable=False)
    previous_hospital_id: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_bed_id: Mapped[str] = mapped_column(String(64), nullable=False)
    new_hospital_id: Mapped[str] = mapped_column(String(64), nullable=True)
    new_bed_id: Mapped[str] = mapped_column(String(64), nullable=True)
    route_progress: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, default=40.0, nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False) # REASSIGNMENT_APPROVED or REASSIGNMENT_REJECTED
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
