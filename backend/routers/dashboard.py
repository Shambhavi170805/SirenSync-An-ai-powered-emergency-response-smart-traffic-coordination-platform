from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.hospital import Hospital
from backend.models.reservation import BedReservation
from backend.models.enums import ReservationStatusEnum
from backend.schemas.bed import BedResponse, BedStatusUpdateRequest
from backend.schemas.queue import HospitalQueueResponse
from backend.schemas.reservation import HospitalReservationItemResponse
from backend.schemas.dashboard import HospitalDashboardOverviewResponse
from backend.schemas.hospital import HospitalDetailResponse
from backend.services.bed_service import (
    BedManagementService,
    HospitalNotFoundException,
    BedNotFoundException
)

router = APIRouter(prefix="/hospitals/{hospital_id}", tags=["Hospital Operations Dashboard"])

@router.get("/dashboard", response_model=HospitalDashboardOverviewResponse)
def get_hospital_dashboard_overview(
    hospital_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns an aggregated operational snapshot for the Hospital Operations Dashboard:
    - Hospital details & capabilities
    - Live bed counts & category breakdown
    - Incoming emergency priority queue
    - Active reservation count & queue metrics
    """
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital '{hospital_id}' not found."
        )

    # 1. Hospital Detail
    total_beds = len(hospital.beds)
    available_beds = sum(1 for b in hospital.beds if b.status.value == "AVAILABLE")
    hosp_detail = HospitalDetailResponse(
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

    # 2. Bed Summary
    bed_summary = BedManagementService.get_hospital_bed_summary(db, hospital_id)

    # 3. Queue Items
    queue_items = BedManagementService.get_hospital_queue(db, hospital_id)
    queue_responses = [
        HospitalQueueResponse.model_validate(q) for q in queue_items
    ]

    # 4. Active Reservations Count
    active_res_count = (
        db.query(BedReservation)
        .filter(
            BedReservation.hospital_id == hospital_id,
            BedReservation.status == ReservationStatusEnum.RESERVED
        )
        .count()
    )

    return HospitalDashboardOverviewResponse(
        hospital=hosp_detail,
        bedSummary=bed_summary,
        queue=queue_responses,
        activeReservationsCount=active_res_count,
        totalQueueCount=len(queue_responses),
        timestamp=datetime.utcnow()
    )

@router.get("/queue", response_model=List[HospitalQueueResponse])
def get_hospital_emergency_queue(
    hospital_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns incoming emergency priority queue for the specified hospital,
    ordered by priority urgency (P1 to P4).
    """
    try:
        items = BedManagementService.get_hospital_queue(db, hospital_id)
        return [HospitalQueueResponse.model_validate(item) for item in items]
    except HospitalNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/reservations", response_model=List[HospitalReservationItemResponse])
def get_hospital_reservations(
    hospital_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns all active and historical bed reservations for the specified hospital,
    including bed numbers, categories, timestamps, and reassignment linkages.
    """
    try:
        res_list = BedManagementService.get_hospital_reservations(db, hospital_id)
        results = []
        for r in res_list:
            results.append(
                HospitalReservationItemResponse(
                    reservationId=r.id,
                    emergencyId=r.emergency_id,
                    hospitalId=r.hospital_id,
                    bedId=r.bed_id,
                    bedNumber=r.bed.bed_number if r.bed else "N/A",
                    bedType=r.bed.bed_type if r.bed else "ICU",
                    status=r.status,
                    reservedAt=r.reserved_at,
                    releasedAt=r.released_at,
                    reassignedToEmergencyId=r.reassigned_to_emergency_id
                )
            )
        return results
    except HospitalNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/beds/{bed_id}/status", response_model=BedResponse)
def update_bed_status(
    hospital_id: str,
    bed_id: str,
    payload: BedStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Allows hospital staff to update bed status (e.g. mark bed as OCCUPIED
    when patient is received, or RELEASE to AVAILABLE when discharged).
    """
    try:
        updated_bed = BedManagementService.update_bed_status(
            db=db,
            hospital_id=hospital_id,
            bed_id=bed_id,
            new_status=payload.status
        )
        return BedResponse.model_validate(updated_bed)
    except BedNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
