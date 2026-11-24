import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.models import Patient
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for SirenSync Emergency Response Patient Authentication",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication with credentials (cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def set_session_cookie(response: Response, session_id: str) -> None:
    """Sets an HTTP-only, secure, SameSite session cookie."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/"
    )

def clear_session_cookie(response: Response) -> None:
    """Deletes the session cookie on response."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE
    )

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "SirenSync Patient Authentication API",
        "database": "SQLite (Persistent)",
        "environment": settings.ENVIRONMENT
    }

@app.post("/api/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(
    payload: PatientRegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Registers a new patient with persistent storage and encrypted password hashing.
    """
    # 1. Verify CAPTCHA challenge
    is_valid_captcha = await verify_captcha(
        payload.captcha_token, 
        client_ip=request.client.host if request.client else None
    )
    if not is_valid_captcha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please complete the security challenge."
        )

    # 2. Check for duplicate email (case-insensitive, normalized)
    normalized_email = payload.email.strip().lower()
    existing_patient = db.query(Patient).filter(Patient.email == normalized_email).first()
    if existing_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    # 3. Hash password using bcrypt
    hashed = hash_password(payload.password)

    # 4. Create patient in database
    new_patient = Patient(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        password_hash=hashed,
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    # 5. Automatically create a session and set HTTP-only cookie
    session_record = create_patient_session(db, new_patient.id)
    set_session_cookie(response, session_record.id)

    return AuthResponse(
        success=True,
        message="Account created successfully",
        patient=PatientProfile.model_validate(new_patient)
    )

@app.post("/api/auth/login", response_model=AuthResponse)
async def login_patient(
    payload: PatientLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticates a patient using email and password, setting an HTTP-only session cookie.
    Uses generic error messages to prevent user enumeration.
    """
    # 1. Verify CAPTCHA challenge
    is_valid_captcha = await verify_captcha(
        payload.captcha_token, 
        client_ip=request.client.host if request.client else None
    )
    if not is_valid_captcha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please complete the security challenge."
        )

    # 2. Query patient
    normalized_email = payload.email.strip().lower()
    patient = db.query(Patient).filter(Patient.email == normalized_email).first()

    # 3. Verify password with bcrypt (constant time check prevents timing attacks)
    if not patient or not verify_password(payload.password, patient.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials and try again."
        )

    # 4. Create session and set HTTP-only cookie
    session_record = create_patient_session(db, patient.id)
    set_session_cookie(response, session_record.id)

    return AuthResponse(
        success=True,
        message="Sign in successful",
        patient=PatientProfile.model_validate(patient)
    )

@app.get("/api/auth/me", response_model=AuthResponse)
async def get_current_user_profile(
    current_patient: Patient = Depends(get_current_patient)
):
    """
    Returns the authenticated patient's profile from the HTTP-only session cookie.
    """
    return AuthResponse(
        success=True,
        message="Authenticated patient profile",
        patient=PatientProfile.model_validate(current_patient)
    )

@app.post("/api/auth/logout", response_model=MessageResponse)
async def logout_patient(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Invalidates the patient's active session and clears the HTTP-only cookie.
    """
    session_id = extract_session_id(request)
    if session_id:
        revoke_patient_session(db, session_id)

    clear_session_cookie(response)
    return MessageResponse(
        success=True,
        message="You have been signed out successfully."
    )
