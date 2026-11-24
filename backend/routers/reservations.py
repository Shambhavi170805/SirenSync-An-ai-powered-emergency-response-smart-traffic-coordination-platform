import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.reservation import BedReservation
from backend.models.hospital import Hospital
from backend.models.emergency import Emergency
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
    EmergencyNotFoundException,
    BedTypeMismatchException,
)
from backend.routers.emergencies import get_authenticated_patient_id
from backend.models.queue import HospitalQueueItem
from backend.services.ambulance_service import AmbulanceDispatchService
from backend.services.tracking_service import tracking_hub

logger = logging.getLogger("sirensync.reservations")

router = APIRouter(prefix="", tags=["Hospital Selection & Bed Reservation"])

@router.post(
    "/emergencies/{emergency_id}/select-hospital",
    response_model=HospitalSelectionResponse,
    status_code=status.HTTP_201_CREATED
)
def select_hospital_and_reserve_bed(
    emergency_id: str,
    request: HospitalSelectionRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Hospital Selection Integration Endpoint.
    Invoked when patient selects a hospital from the ranked list in Shambhavi's UI.
    Validates bed availability, executes transaction-safe atomic bed locking,
    and designates the selected hospital as the coordinating authority.
    """
    # Privacy & ownership check: Verify caller owns this emergency if authenticated
    auth_patient_id = get_authenticated_patient_id(req)
    if auth_patient_id:
        emg = db.query(Emergency).filter(Emergency.id == emergency_id).first()
        if emg and emg.patient_id != auth_patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot select a hospital for another patient's emergency."
            )

    try:
        reservation, bed = BedManagementService.reserve_bed_atomically(
            db=db,
            hospital_id=request.selectedHospitalId,
            bed_type=request.requiredBedType,
            emergency_id=emergency_id
        )

        hospital = db.query(Hospital).filter(Hospital.id == request.selectedHospitalId).one()

        # Bed reservation is committed by reserve_bed_atomically before dispatch begins.
        # A missing eligible ambulance must never undo the secured bed reservation.
        ambulance_info = None
        dispatch_status = "AMBULANCE_PENDING"
        try:
            ambulance_info = AmbulanceDispatchService.dispatch_for_emergency(
                db=db,
                emergency_id=emergency_id,
                hospital_id=request.selectedHospitalId,
            )
            if ambulance_info:
                dispatch_status = "AMBULANCE_DISPATCHED"
                tracking_hub.broadcast_event_threadsafe(
                    event_type="AMBULANCE_DISPATCHED",
                    payload=ambulance_info.model_dump(mode="json"),
                    emergency_id=emergency_id,
                )
        except Exception:
            # Dispatch is a separate transaction. Preserve the already-committed bed reservation.
            db.rollback()
            logger.exception("Ambulance dispatch failed after bed reservation for %s", emergency_id)
            dispatch_status = "AMBULANCE_PENDING"

        if dispatch_status == "AMBULANCE_PENDING":
            queue_item = db.query(HospitalQueueItem).filter(
                HospitalQueueItem.emergency_id == emergency_id
            ).first()
            if queue_item:
                if not queue_item.dispatch_pending_since:
                    queue_item.dispatch_pending_since = __import__("datetime").datetime.utcnow()
                queue_item.notes = "Bed reserved. Automatic ambulance matching and dispatch retry are active."
                db.commit()

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
                dispatchStatus=dispatch_status
            ),
            ambulance=ambulance_info,
            dispatchStatus=dispatch_status,
            message=("Bed reserved and ambulance dispatched." if ambulance_info else "Bed reserved securely. Ambulance dispatch is pending; the reservation remains protected.")
        )

    except BedTypeMismatchException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bed type mismatch: {str(e)}"
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
    except EmergencyNotFoundException as e:
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
