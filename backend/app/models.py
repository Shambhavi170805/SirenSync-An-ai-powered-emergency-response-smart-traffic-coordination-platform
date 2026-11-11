import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def generate_patient_id():
    # Human-friendly ID format: PAT-XXXX
    return f"PAT-{uuid.uuid4().hex[:8].upper()}"

def utcnow():
    return datetime.now(timezone.utc)

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(64), primary_key=True, default=generate_patient_id, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True, default="+91 98765 43210")
    blood_group = Column(String(10), nullable=True, default="O+")
    emergency_contact_name = Column(String(100), nullable=True, default="Emergency Contact")
    emergency_contact_phone = Column(String(30), nullable=True, default="+91 94120 54321")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    sessions = relationship("UserSession", back_populates="patient", cascade="all, delete-orphan")

class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    patient = relationship("Patient", back_populates="sessions")
