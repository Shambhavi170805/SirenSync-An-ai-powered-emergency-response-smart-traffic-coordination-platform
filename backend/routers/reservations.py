from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.reservation import BedReservation
from backend.models.hospital import Hospital
from backend.schemas.reservation import (
    HospitalSelectionRequest,
    HospitalSelectionResponse,
    BedReservationDetail,
    CoordinatingHospitalInfo,
)
from backend.services.bed_service import (
    BedManagementService,
    BedNotAvailableException,
    BedReservationConflictException,
    HospitalNotFoundException,
)

router = APIRouter(prefix="", tags=["Hospital Selection & Bed Reservation"])

@router.post(
    "/emergencies/{emergency_id}/select-hospital",
    response_model=HospitalSelectionResponse,
    status_code=status.HTTP_201_CREATED
)
def select_hospital_and_reserve_bed(
    emergency_id: str,
    request: HospitalSelectionRequest,
    db: Session = Depends(get_db)
):
    """
    Hospital Selection Integration Endpoint.
    Invoked when patient selects a hospital from the ranked list in Shambhavi's UI.
    Validates bed availability, executes transaction-safe atomic bed locking,
    and designates the selected hospital as the coordinating authority.
    """
    try:
        reservation, bed = BedManagementService.reserve_bed_atomically(
            db=db,
            hospital_id=request.selectedHospitalId,
            bed_type=request.requiredBedType,
            emergency_id=emergency_id
        )

        hospital = db.query(Hospital).filter(Hospital.id == request.selectedHospitalId).one()

        return HospitalSelectionResponse(
            status="SUCCESS",
            emergencyId=emergency_id,
            hospitalId=hospital.id,
            reservation=BedReservationDetail(
                reservationId=reservation.id,
                bedId=bed.id,
                bedNumber=bed.bed_number,
                bedType=bed.bed_type,
                status=reservation.status,
                reservedAt=reservation.reserved_at
            ),
            coordinatingHospital=CoordinatingHospitalInfo(
                hospitalId=hospital.id,
                hospitalName=hospital.name,
                contactNumber=hospital.contact_number,
                address=hospital.address,
                dispatchStatus="AMBULANCE_COORDINATION_INITIATED"
            ),
            message="Bed reserved securely. Hospital is now the coordinating authority."
        )

    except BedNotAvailableException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resource conflict: {str(e)}"
        )
    except BedReservationConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resource conflict: {str(e)}"
        )
    except HospitalNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/reservations/{reservation_id}", response_model=BedReservationDetail)
def get_reservation_details(reservation_id: str, db: Session = Depends(get_db)):
    """
    Fetches live details of a specific bed reservation.
    """
    reservation = db.query(BedReservation).filter(BedReservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation '{reservation_id}' not found."
        )

    return BedReservationDetail(
        reservationId=reservation.id,
        bedId=reservation.bed.id,
        bedNumber=reservation.bed.bed_number,
        bedType=reservation.bed.bed_type,
        status=reservation.status,
        reservedAt=reservation.reserved_at
    )
