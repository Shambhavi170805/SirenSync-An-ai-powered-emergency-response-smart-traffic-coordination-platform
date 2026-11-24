import secrets
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Patient, UserSession
from app.config import settings

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), 
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def create_patient_session(db: Session, patient_id: str) -> UserSession:
    """Generates a secure random session token and persists it in SQLite."""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)
    
    session_record = UserSession(
        id=session_id,
        patient_id=patient_id,
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record

def revoke_patient_session(db: Session, session_id: str) -> bool:
    """Marks a session as revoked."""
    session_record = db.query(UserSession).filter(UserSession.id == session_id).first()
    if session_record:
        session_record.is_revoked = True
        db.commit()
        return True
    return False

def extract_session_id(request: Request) -> str | None:
    """Extracts session token from HTTP-only cookie or Authorization header."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        return token
    
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None

async def get_current_patient(
    request: Request, 
    db: Session = Depends(get_db)
) -> Patient:
    """
    Dependency that authenticates the patient from the HTTP-only cookie session.
    Returns 401 Unauthorized if missing, expired, or revoked.
    """
    session_id = extract_session_id(request)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Cookie"}
        )

    session_record = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.is_revoked.is_(False)
        )
        .first()
    )

    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or was revoked. Please sign in again.",
            headers={"WWW-Authenticate": "Cookie"}
        )

    # Check expiration
    now = datetime.now(timezone.utc)
    # Ensure timezone awareness for comparison
    expires_at = session_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        session_record.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Cookie"}
        )

    patient = db.query(Patient).filter(Patient.id == session_record.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient account not found.",
            headers={"WWW-Authenticate": "Cookie"}
        )

    return patient
