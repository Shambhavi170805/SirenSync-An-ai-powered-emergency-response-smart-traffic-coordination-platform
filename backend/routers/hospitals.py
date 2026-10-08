from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.hospital import Hospital
from backend.schemas.hospital import HospitalResponse, HospitalDetailResponse

router = APIRouter(prefix="/hospitals", tags=["Hospitals"])

@router.get("", response_model=List[HospitalResponse])
def list_hospitals(db: Session = Depends(get_db)):
    """
    Returns directory of all active hospitals with their capabilities.
    """
    hospitals = db.query(Hospital).filter(Hospital.is_active == True).all()
    return hospitals

@router.get("/{hospital_id}", response_model=HospitalDetailResponse)
def get_hospital_details(hospital_id: str, db: Session = Depends(get_db)):
    """
    Returns specific hospital details including capabilities and bed summary totals.
    """
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital '{hospital_id}' not found."
        )

    total_beds = len(hospital.beds)
    available_beds = sum(1 for b in hospital.beds if b.status.value == "AVAILABLE")

    return HospitalDetailResponse(
        id=hospital.id,
        name=hospital.name,
        address=hospital.address,
        latitude=hospital.latitude,
        longitude=hospital.longitude,
        contact_number=hospital.contact_number,
        is_active=hospital.is_active,
        created_at=hospital.created_at,
        capabilities=[
            {"capability_code": c.capability_code, "description": c.description}
            for c in hospital.capabilities
        ],
        total_beds=total_beds,
        available_beds=available_beds
    )
