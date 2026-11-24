import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Patient Auth imports
from app.config import settings as auth_settings
from app.database import get_db as get_auth_db, init_db as init_auth_db
from app.models import Patient as AuthPatient
from app.schemas import (
    PatientRegisterRequest,
    PatientLoginRequest,
    PatientProfile,
    AuthResponse,
    MessageResponse
)
from app.auth import (
    hash_password,
    verify_password,
    create_patient_session,
    revoke_patient_session,
    extract_session_id,
    get_current_patient
)
from app.captcha import verify_captcha

# Hospital Intelligence imports
from backend.config import settings as hospital_settings
from backend.database.init_db import init_db as init_hospital_db
from backend.routers import (
    hospitals_router,
    beds_router,
    ranking_router,
    reservations_router,
    reassignment_router,
    dashboard_router,
    emergencies_router,
    ambulances_router,
    tracking_router,
)
from backend.services.tracking_service import tracking_hub
from backend.database.session import SessionLocal
from backend.models.queue import HospitalQueueItem
from backend.models.reservation import BedReservation
from backend.models.ambulance import Ambulance
from backend.models.enums import QueueStatusEnum, ReservationStatusEnum
from backend.services.ambulance_service import AmbulanceDispatchService
import logging

logger = logging.getLogger("sirensync.dispatch")


def _retry_pending_dispatches_once():
    db = SessionLocal()
    try:
        pending_items = db.query(HospitalQueueItem).filter(
            HospitalQueueItem.status == QueueStatusEnum.COORDINATING,
            HospitalQueueItem.dispatch_pending_since.is_not(None),
        ).all()
        for item in pending_items:
            reservation = db.query(BedReservation).filter(
                BedReservation.emergency_id == item.emergency_id,
                BedReservation.status == ReservationStatusEnum.RESERVED,
            ).first()
            if not reservation:
                continue
            already_assigned = db.query(Ambulance).filter(
                Ambulance.assigned_emergency_id == item.emergency_id
            ).first()
            if already_assigned:
                continue
            try:
                assigned = AmbulanceDispatchService.dispatch_for_emergency(
                    db, item.emergency_id, item.hospital_id
                )
                if assigned:
                    dispatch_payload = assigned.model_dump(mode="json")
                    dispatch_payload["emergencyId"] = item.emergency_id
                    tracking_hub.broadcast_event_threadsafe(
                        "AMBULANCE_DISPATCHED", dispatch_payload, item.emergency_id
                    )
                    logger.info("Pending emergency %s dispatched to %s", item.emergency_id, assigned.vehicleNumber)
            except Exception:
                db.rollback()
                logger.exception("Automatic ambulance retry failed for emergency %s", item.emergency_id)
    finally:
        db.close()


async def _pending_dispatch_worker():
    while True:
        await asyncio.sleep(10)
        try:
            await asyncio.to_thread(_retry_pending_dispatches_once)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Pending ambulance dispatch worker iteration failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the existing patient-auth and hospital/ambulance database layers.
    init_auth_db()
    init_hospital_db()
    tracking_hub.set_event_loop(asyncio.get_running_loop())
    retry_task = asyncio.create_task(_pending_dispatch_worker())
    try:
        yield
    finally:
        retry_task.cancel()
        try:
            await retry_task
        except asyncio.CancelledError:
            pass
        tracking_hub.set_event_loop(None)

app = FastAPI(
    title="SirenSync Unified Platform API",
    version="2.0.0",
    description=(
        "SirenSync Integrated Backend API: Patient Experience & Intake + Hospital Intelligence & Bed Management + Ambulance Dispatch & Tracking.\n\n"
        "- Patient Authentication & Persistent Session Management (SQLite + Bcrypt)\n"
        "- Deterministic 4-Factor Hospital Ranking Engine (Distance, Capability, Traffic, Bed Availability)\n"
        "- Concurrency-Safe Transactional Bed Reservation (Atomic Compare-and-Swap Locking)\n"
        "- Hospital Operations Dashboard & Inbound Queue Tracking\n"
        "- Ambulance Fleet Dispatch, Driver Workflow & Real-Time Tracking"
    ),
    lifespan=lifespan
)

# CORS middleware enabling credentials for frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 1. Mount Static Hospital Operations Dashboard UI
# ============================================================================
frontend_hospital_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "hospital"
)
if os.path.exists(frontend_hospital_dir):
    app.mount("/dashboard", StaticFiles(directory=frontend_hospital_dir, html=True), name="dashboard")

frontend_driver_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "driver"
)
if os.path.exists(frontend_driver_dir):
    app.mount("/driver", StaticFiles(directory=frontend_driver_dir, html=True), name="driver")

# ============================================================================
# 2. Register Hospital Intelligence & Bed Management Routers (/api/v1)
# ============================================================================
app.include_router(emergencies_router, prefix=hospital_settings.API_V1_PREFIX)
app.include_router(hospitals_router, prefix=hospital_settings.API_V1_PREFIX)
app.include_router(beds_router, prefix=hospital_settings.API_V1_PREFIX)
app.include_router(ranking_router, prefix=hospital_settings.API_V1_PREFIX)
app.include_router(reservations_router, prefix=hospital_settings.API_V1_PREFIX)
app.include_router(reassignment_router, prefix=hospital_settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=hospital_settings.API_V1_PREFIX)
app.include_router(ambulances_router, prefix=hospital_settings.API_V1_PREFIX)
app.include_router(tracking_router, prefix=hospital_settings.API_V1_PREFIX)

# ============================================================================
# 3. Patient Authentication Endpoints (/api/auth and /api/v1/auth)
# ============================================================================
from fastapi import APIRouter

auth_router = APIRouter()

def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=auth_settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=auth_settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite=auth_settings.COOKIE_SAMESITE,
        secure=auth_settings.COOKIE_SECURE,
        path="/"
    )

def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=auth_settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=auth_settings.COOKIE_SAMESITE,
        secure=auth_settings.COOKIE_SECURE
    )

@auth_router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, tags=["Patient Authentication"])
async def register_patient(
    payload: PatientRegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_auth_db)
):
    """Registers a new patient account with persistent storage and bcrypt hashing."""
    is_valid_captcha = await verify_captcha(
        payload.captcha_token,
        client_ip=request.client.host if request.client else None
    )
    if not is_valid_captcha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please complete the security challenge."
        )

    normalized_email = payload.email.strip().lower()
    existing_patient = db.query(AuthPatient).filter(AuthPatient.email == normalized_email).first()
    if existing_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    hashed = hash_password(payload.password)
    new_patient = AuthPatient(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        password_hash=hashed,
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    session_record = create_patient_session(db, new_patient.id)
    set_session_cookie(response, session_record.id)

    return AuthResponse(
        success=True,
        message="Account created successfully",
        patient=PatientProfile.model_validate(new_patient)
    )

@auth_router.post("/login", response_model=AuthResponse, tags=["Patient Authentication"])
async def login_patient(
    payload: PatientLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_auth_db)
):
    """Authenticates patient and sets HTTP-only session cookie."""
    is_valid_captcha = await verify_captcha(
        payload.captcha_token,
        client_ip=request.client.host if request.client else None
    )
    if not is_valid_captcha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please complete the security challenge."
        )

    normalized_email = payload.email.strip().lower()
    patient = db.query(AuthPatient).filter(AuthPatient.email == normalized_email).first()

    if not patient or not verify_password(payload.password, patient.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials and try again."
        )

    session_record = create_patient_session(db, patient.id)
    set_session_cookie(response, session_record.id)

    return AuthResponse(
        success=True,
        message="Sign in successful",
        patient=PatientProfile.model_validate(patient)
    )

@auth_router.get("/me", response_model=AuthResponse, tags=["Patient Authentication"])
async def get_current_user_profile(
    current_patient: AuthPatient = Depends(get_current_patient)
):
    """Returns the authenticated patient's profile from HTTP-only session cookie."""
    return AuthResponse(
        success=True,
        message="Authenticated patient profile",
        patient=PatientProfile.model_validate(current_patient)
    )

@auth_router.post("/logout", response_model=MessageResponse, tags=["Patient Authentication"])
async def logout_patient(
    request: Request,
    response: Response,
    db: Session = Depends(get_auth_db)
):
    """Invalidates active patient session and clears cookie."""
    session_id = extract_session_id(request)
    if session_id:
        revoke_patient_session(db, session_id)

    clear_session_cookie(response)
    return MessageResponse(
        success=True,
        message="You have been signed out successfully."
    )

# Register auth router under both /api/auth and /api/v1/auth
app.include_router(auth_router, prefix="/api/auth")
app.include_router(auth_router, prefix="/api/v1/auth")

# ============================================================================
# 4. System Health & Metadata Endpoints
# ============================================================================
@app.get("/", tags=["System Health"])
def root():
    return {
        "service": "SirenSync Unified Platform",
        "subsystems": {
            "patientIntake": "Operational (React UI /api/auth)",
            "hospitalIntelligence": "Operational (FastAPI /api/v1)",
            "dashboard": "/dashboard/",
            "docs": "/docs"
        },
        "status": "OPERATIONAL",
        "version": "2.0.0"
    }

@app.get("/health", tags=["System Health"])
def health_check():
    return {"status": "HEALTHY", "service": "sirensync-unified"}

@app.get("/api/health", tags=["System Health"])
def api_health():
    return {
        "status": "ok",
        "service": "SirenSync Unified API",
        "databases": {
            "patientAuth": "SQLite (sirensync.db)",
            "hospitalIntelligence": "SQLite WAL (sirensync_hospital.db)"
        }
    }
