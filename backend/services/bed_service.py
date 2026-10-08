import uuid
from datetime import datetime
from typing import Optional, Tuple, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import update, select
from backend.models.bed import Bed
from backend.models.hospital import Hospital
from backend.models.reservation import BedReservation
from backend.models.queue import HospitalQueueItem
from backend.models.emergency import Emergency
from backend.models.enums import BedStatusEnum, BedTypeEnum, ReservationStatusEnum, QueueStatusEnum, PriorityEnum
from backend.schemas.bed import BedCategoryCount, HospitalBedSummaryResponse

class BedNotAvailableException(Exception):
    """Raised when no bed of the requested category is available."""
    pass

class BedReservationConflictException(Exception):
    """Raised when a specific bed was claimed concurrently by another transaction."""
    pass

class HospitalNotFoundException(Exception):
    """Raised when the specified hospital does not exist."""
    pass

class BedNotFoundException(Exception):
    """Raised when a specific bed does not exist in the hospital."""
    pass

class BedManagementService:
    """
    Transaction-safe Bed Management and Concurrency Locking Service.
    Enforces atomic compare-and-swap (CAS) transitions: AVAILABLE -> RESERVED.
    Guarantees no race condition or double-booking across concurrent threads.
    """

    @staticmethod
    def reserve_bed_atomically(
        db: Session,
        hospital_id: str,
        bed_type: BedTypeEnum,
        emergency_id: str,
        specific_bed_id: Optional[str] = None
    ) -> Tuple[BedReservation, Bed]:
        """
        Executes within an isolated database transaction.
        Attempts atomic conditional lock on an available bed.
        If successful, persists BedReservation and updates HospitalQueue in the same atomic commit.
        If another transaction claims the bed simultaneously, rolls back cleanly and raises a conflict.
        """
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HospitalNotFoundException(f"Hospital '{hospital_id}' not found.")

        # Ensure Emergency record exists for reference integrity
        emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
        if not emergency:
            # If emergency not yet registered by Shambhavi, create placeholder with required fields
            emergency = Emergency(
                id=emergency_id,
                patient_id=f"pat-{uuid.uuid4().hex[:6]}",
                emergency_type="GENERAL_EMERGENCY",
                priority=PriorityEnum.P2_EMERGENCY,
                patient_latitude=hospital.latitude,
                patient_longitude=hospital.longitude,
                required_bed_type=bed_type,
                selected_hospital_id=hospital_id
            )
            db.add(emergency)
            db.flush()
        else:
            emergency.selected_hospital_id = hospital_id
            db.flush()

        # Determine target candidates
        if specific_bed_id:
            candidate_ids = [specific_bed_id]
        else:
            # Fetch all candidate beds currently marked AVAILABLE
            candidates = (
                db.query(Bed.id)
                .filter(
                    Bed.hospital_id == hospital_id,
                    Bed.bed_type == bed_type,
                    Bed.status == BedStatusEnum.AVAILABLE
                )
                .order_by(Bed.bed_number.asc())
                .all()
            )
            candidate_ids = [c[0] for c in candidates]

        if not candidate_ids:
            raise BedNotAvailableException(
                f"No available {bed_type.value} beds at hospital '{hospital.name}'."
            )

        reservation_successful = False
        acquired_bed_id = None

        # Attempt atomic compare-and-swap on candidate beds
        for cand_id in candidate_ids:
            try:
                # Atomic CAS update query:
                # Only updates if status is STILL 'AVAILABLE' at the moment of execution
                stmt = (
                    update(Bed)
                    .where(Bed.id == cand_id)
                    .where(Bed.hospital_id == hospital_id)
                    .where(Bed.status == BedStatusEnum.AVAILABLE)
                    .values(
                        status=BedStatusEnum.RESERVED,
                        version=Bed.version + 1,
                        updated_at=datetime.utcnow()
                    )
                )
                res = db.execute(stmt)

                if res.rowcount == 1:
                    # Successfully acquired lock on this specific bed!
                    acquired_bed_id = cand_id
                    reservation_successful = True
                    break
            except Exception:
                db.rollback()
                raise

        if not reservation_successful or not acquired_bed_id:
            db.rollback()
            if specific_bed_id:
                raise BedReservationConflictException(
                    f"Requested bed '{specific_bed_id}' is no longer available (concurrently reserved)."
                )
            raise BedNotAvailableException(
                f"All {bed_type.value} beds at '{hospital.name}' were locked by concurrent requests."
            )

        try:
            # Create the reservation record in the same atomic transaction
            res_id = f"res-{uuid.uuid4().hex[:8]}"
            reservation = BedReservation(
                id=res_id,
                emergency_id=emergency_id,
                hospital_id=hospital_id,
                bed_id=acquired_bed_id,
                status=ReservationStatusEnum.RESERVED,
                reserved_at=datetime.utcnow()
            )
            db.add(reservation)

            # Update or create HospitalQueueItem
            queue_item = (
                db.query(HospitalQueueItem)
                .filter(HospitalQueueItem.emergency_id == emergency_id)
                .first()
            )
            if not queue_item:
                queue_item = HospitalQueueItem(
                    id=f"qitem-{uuid.uuid4().hex[:8]}",
                    hospital_id=hospital_id,
                    emergency_id=emergency_id,
                    priority=emergency.priority,
                    status=QueueStatusEnum.COORDINATING,
                    route_progress=0.0,
                    notes=f"Bed {acquired_bed_id} locked. Coordinating ambulance dispatch."
                )
                db.add(queue_item)
            else:
                queue_item.hospital_id = hospital_id
                queue_item.status = QueueStatusEnum.COORDINATING

            # Commit the entire transaction atomically
            db.commit()

            # Refresh and return
            locked_bed = db.query(Bed).filter(Bed.id == acquired_bed_id).one()
            db.refresh(reservation)
            return reservation, locked_bed

        except Exception as e:
            # Guarantee rollback on failure: bed state is never left in partial RESERVED state
            db.rollback()
            raise e

    @staticmethod
    def release_reservation(
        db: Session,
        reservation_id: str,
        reason: str = "MANUAL_RELEASE"
    ) -> bool:
        """
        Releases an active reservation and resets the bed status to AVAILABLE.
        """
        try:
            reservation = db.query(BedReservation).filter(BedReservation.id == reservation_id).first()
            if not reservation:
                return False

            reservation.status = ReservationStatusEnum.RELEASED_FOR_REASSIGNMENT
            reservation.released_at = datetime.utcnow()

            # Reset bed
            bed = db.query(Bed).filter(Bed.id == reservation.bed_id).first()
            if bed and bed.status == BedStatusEnum.RESERVED:
                bed.status = BedStatusEnum.AVAILABLE
                bed.updated_at = datetime.utcnow()

            db.commit()
            return True
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_hospital_bed_summary(db: Session, hospital_id: str) -> HospitalBedSummaryResponse:
        """
        Returns structured summary counts of beds by category and status.
        """
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HospitalNotFoundException(f"Hospital '{hospital_id}' not found.")

        by_cat: Dict[str, BedCategoryCount] = {
            bt.value: BedCategoryCount(available=0, reserved=0, occupied=0, total=0)
            for bt in BedTypeEnum
        }

        total = 0
        available = 0
        reserved = 0
        occupied = 0

        for bed in hospital.beds:
            total += 1
            btype = bed.bed_type.value
            by_cat[btype].total += 1

            if bed.status == BedStatusEnum.AVAILABLE:
                available += 1
                by_cat[btype].available += 1
            elif bed.status == BedStatusEnum.RESERVED:
                reserved += 1
                by_cat[btype].reserved += 1
            elif bed.status == BedStatusEnum.OCCUPIED:
                occupied += 1
                by_cat[btype].occupied += 1

        return HospitalBedSummaryResponse(
            hospital_id=hospital_id,
            total_beds=total,
            available_beds=available,
            reserved_beds=reserved,
            occupied_beds=occupied,
            by_category=by_cat
        )

    @staticmethod
    def update_bed_status(
        db: Session,
        hospital_id: str,
        bed_id: str,
        new_status: BedStatusEnum
    ) -> Bed:
        """
        Updates bed status for hospital resource management operations.
        Ensures bed exists and belongs to the specified hospital.
        """
        bed = (
            db.query(Bed)
            .filter(Bed.id == bed_id, Bed.hospital_id == hospital_id)
            .first()
        )
        if not bed:
            raise BedNotFoundException(f"Bed '{bed_id}' not found in hospital '{hospital_id}'.")
        
        bed.status = new_status
        bed.version = Bed.version + 1
        bed.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(bed)
        return bed

    @staticmethod
    def get_hospital_reservations(db: Session, hospital_id: str):
        """
        Returns all reservations associated with a hospital, with bed details.
        """
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HospitalNotFoundException(f"Hospital '{hospital_id}' not found.")

        reservations = (
            db.query(BedReservation)
            .filter(BedReservation.hospital_id == hospital_id)
            .order_by(BedReservation.reserved_at.desc())
            .all()
        )
        return reservations

    @staticmethod
    def get_hospital_queue(db: Session, hospital_id: str):
        """
        Returns all queue items for a hospital ordered by priority (P1 first) and created_at.
        """
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HospitalNotFoundException(f"Hospital '{hospital_id}' not found.")

        items = (
            db.query(HospitalQueueItem)
            .filter(HospitalQueueItem.hospital_id == hospital_id)
            .order_by(HospitalQueueItem.created_at.desc())
            .all()
        )
        priority_order = {
            PriorityEnum.P1_CRITICAL: 1,
            PriorityEnum.P2_EMERGENCY: 2,
            PriorityEnum.P3_URGENT: 3,
            PriorityEnum.P4_NON_URGENT: 4
        }
        return sorted(items, key=lambda x: priority_order.get(x.priority, 5))

