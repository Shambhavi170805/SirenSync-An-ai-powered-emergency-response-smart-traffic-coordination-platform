import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.emergency import Emergency
from backend.schemas.emergency import EmergencyCreateRequest, EmergencyResponse

router = APIRouter(prefix="/emergencies", tags=["Emergency Intake & Lifecycle"])

def get_authenticated_patient_id(request: Request) -> Optional[str]:
    """
    Safely resolves the authenticated patient ID from the HTTP-only session cookie
    in sirensync.db without exposing passwords, hashes, or session secrets.
    Returns None if the request is unauthenticated (guest intake).
    """
    token = request.cookies.get("sirensync_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        return None

    try:
        from app.database import SessionLocal as AuthSessionLocal
        from app.models import UserSession as AuthSession
        with AuthSessionLocal() as auth_db:
            now = datetime.now(timezone.utc)
            session_rec = (
                auth_db.query(AuthSession)
                .filter(
                    AuthSession.id == token,
                    AuthSession.is_revoked.is_(False)
                )
                .first()
            )
            if session_rec:
                exp = session_rec.expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp > now:
                    return session_rec.patient_id
    except Exception as exc:
        # Graceful fallback if auth DB is not initialized or unreachable
        pass

    return None

@router.post(
    "",
    response_model=EmergencyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Emergency Intake",
    description=(
        "Registers and persists an authoritative emergency record in the hospital subsystem. "
        "Derives the authentic patient ID from the authenticated session when present. "
        "Supports idempotent retries and validates clinical priority, coordinates, and bed type."
    )
)
def register_emergency(
    payload: EmergencyCreateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    # 1. Resolve Emergency ID: generate if not supplied by client
    emergency_id = (payload.emergencyId or "").strip()
    if not emergency_id:
        emergency_id = f"emg-{uuid.uuid4().hex[:8]}"

    # 2. Derive Patient ID securely from server-side session; fallback to payload or anon
    auth_patient_id = get_authenticated_patient_id(request)
    patient_id = auth_patient_id or payload.patientId or f"pat-{emergency_id}"

    # 3. Idempotency check: see if emergency with this ID already exists
    existing = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if existing:
        conflicts = []
        if existing.emergency_type != payload.emergencyType:
            conflicts.append(f"emergencyType ('{payload.emergencyType}' vs registered '{existing.emergency_type}')")
        if existing.priority != payload.priority:
            conflicts.append(f"priority ('{payload.priority.value}' vs registered '{existing.priority.value}')")
        if existing.required_bed_type != payload.requiredBedType:
            conflicts.append(f"requiredBedType ('{payload.requiredBedType.value}' vs registered '{existing.required_bed_type.value}')")
        if patient_id and existing.patient_id != patient_id:
            conflicts.append(f"patientId ('{patient_id}' vs registered '{existing.patient_id}')")
        if payload.symptoms and existing.symptoms and existing.symptoms != payload.symptoms:
            conflicts.append(f"symptoms ('{payload.symptoms}' vs registered '{existing.symptoms}')")
        if (
            abs(existing.patient_latitude - payload.patientLocation.latitude) > 0.001 or
            abs(existing.patient_longitude - payload.patientLocation.longitude) > 0.001
        ):
            conflicts.append("patientLocation coordinates do not match registered coordinates")

        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Emergency '{emergency_id}' is already registered with conflicting data: "
                    f"{', '.join(conflicts)}. Duplicate registrations must not conflict."
                )
            )

        # Idempotent re-submission with identical core data returns existing record
        response.status_code = status.HTTP_200_OK
        return EmergencyResponse.from_orm_model(existing)

    # 4. Create and persist authentic emergency record
    emergency = Emergency(
        id=emergency_id,
        patient_id=patient_id,
        emergency_type=payload.emergencyType,
        priority=payload.priority,
        patient_latitude=payload.patientLocation.latitude,
        patient_longitude=payload.patientLocation.longitude,
        patient_address=payload.patientLocation.address,
        required_bed_type=payload.requiredBedType,
        symptoms=payload.symptoms,
        region=payload.region or "Dehradun",
        selected_hospital_id=None
    )
    db.add(emergency)
    db.commit()
    db.refresh(emergency)

    return EmergencyResponse.from_orm_model(emergency)

@router.get(
    "/patient/my-emergencies",
    response_model=List[EmergencyResponse],
    summary="Get Current Patient's Emergencies",
    description="Returns all emergency records owned by the authenticated patient session."
)
def get_my_emergencies(
    request: Request,
    db: Session = Depends(get_db)
):
    patient_id = get_authenticated_patient_id(request)
    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view your emergency records."
        )

    records = (
        db.query(Emergency)
        .filter(Emergency.patient_id == patient_id)
        .order_by(Emergency.created_at.desc())
        .all()
    )
    return [EmergencyResponse.from_orm_model(e) for e in records]

@router.get(
    "/{emergency_id}",
    response_model=EmergencyResponse,
    summary="Get Emergency Record",
    description="Fetches an authoritative persisted emergency record by its shared identifier."
)
def get_emergency(
    emergency_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emergency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emergency '{emergency_id}' not found."
        )

    # Privacy check: If the caller is an authenticated patient, verify they own this record
    auth_patient_id = get_authenticated_patient_id(request)
    if auth_patient_id and emergency.patient_id != auth_patient_id:
        # Note: Hospital staff/dashboards without patient session are permitted for clinical triage
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not authorized to view another patient's emergency record."
        )

    return EmergencyResponse.from_orm_model(emergency)
