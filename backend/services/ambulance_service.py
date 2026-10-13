from typing import Optional, List, Dict, Set
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import update
from backend.models.ambulance import Ambulance
from backend.models.emergency import Emergency
from backend.models.hospital import Hospital
from backend.models.queue import HospitalQueueItem
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum, PriorityEnum, QueueStatusEnum
from backend.schemas.ambulance import (
    AmbulanceDispatchInfo,
    AmbulanceDetailResponse,
    TrackingSnapshotResponse,
)
from backend.shared.contracts import CoordinatesContract, RerouteEventContract
from backend.services.ranking_service import calculate_haversine_distance

# Valid operational lifecycle transitions for ambulances
VALID_STATUS_TRANSITIONS: Dict[AmbulanceStatusEnum, Set[AmbulanceStatusEnum]] = {
    AmbulanceStatusEnum.AVAILABLE: {AmbulanceStatusEnum.ASSIGNED, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.ASSIGNED: {AmbulanceStatusEnum.EN_ROUTE_PICKUP, AmbulanceStatusEnum.AVAILABLE, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.EN_ROUTE_PICKUP: {AmbulanceStatusEnum.PATIENT_ONBOARD, AmbulanceStatusEnum.AVAILABLE, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.PATIENT_ONBOARD: {AmbulanceStatusEnum.EN_ROUTE_HOSPITAL, AmbulanceStatusEnum.ARRIVED, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.EN_ROUTE_HOSPITAL: {AmbulanceStatusEnum.ARRIVED, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.ARRIVED: {AmbulanceStatusEnum.AVAILABLE, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.MAINTENANCE: {AmbulanceStatusEnum.AVAILABLE},
}

class AmbulanceDispatchService:
    """
    Hospital-Coordinated Ambulance Dispatch & Tracking Service (Member 3 - Nidhi).
    Integrates with hospital selection, bed reservation, real-time telemetry,
    and priority reassignment reroutes.
    """

    @staticmethod
    def dispatch_for_emergency(
        db: Session,
        emergency_id: str,
        hospital_id: str
    ) -> Optional[AmbulanceDispatchInfo]:
        """
        Dispatches an eligible available ambulance to the patient after successful bed reservation.
        """
        # 1. Idempotency Check
        existing_assignment = (
            db.query(Ambulance)
            .filter(Ambulance.assigned_emergency_id == emergency_id)
            .first()
        )
        if existing_assignment:
            return AmbulanceDispatchService._to_dispatch_info(db, existing_assignment, emergency_id)

        # 2. Fetch emergency details
        emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
        p_lat = emergency.patient_latitude if emergency else 12.9716
        p_lng = emergency.patient_longitude if emergency else 77.5946
        priority = emergency.priority if emergency else PriorityEnum.P2_EMERGENCY

        # 3. Query AVAILABLE ambulances
        candidates = (
            db.query(Ambulance)
            .filter(
                Ambulance.status == AmbulanceStatusEnum.AVAILABLE,
                Ambulance.assigned_emergency_id.is_(None)
            )
            .all()
        )

        if not candidates:
            qitem = db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emergency_id).first()
            if qitem:
                qitem.notes = "Bed reserved securely. Waiting for available ambulance dispatch."
                db.commit()
            return None

        # 4. Score and sort candidates
        def candidate_sort_key(amb: Ambulance):
            type_score = 0
            if priority == PriorityEnum.P1_CRITICAL:
                if amb.ambulance_type in (AmbulanceTypeEnum.MICU, AmbulanceTypeEnum.ALS):
                    type_score = -2
                if "VENTILATOR" in (amb.equipment_tags or "").upper():
                    type_score -= 1
            elif priority == PriorityEnum.P2_EMERGENCY:
                if amb.ambulance_type in (AmbulanceTypeEnum.ALS, AmbulanceTypeEnum.BLS):
                    type_score = -1

            dist_km = calculate_haversine_distance(
                p_lat, p_lng, amb.current_latitude, amb.current_longitude
            )
            return (type_score, dist_km)

        candidates.sort(key=candidate_sort_key)

        # 5. Atomic Compare-and-Swap (CAS)
        acquired_amb_id: Optional[str] = None
        for cand in candidates:
            try:
                stmt = (
                    update(Ambulance)
                    .where(Ambulance.id == cand.id)
                    .where(Ambulance.status == AmbulanceStatusEnum.AVAILABLE)
                    .where(Ambulance.assigned_emergency_id.is_(None))
                    .values(
                        status=AmbulanceStatusEnum.ASSIGNED,
                        assigned_emergency_id=emergency_id,
                        destination_hospital_id=hospital_id,
                        route_progress=0.0,
                        version=Ambulance.version + 1,
                        updated_at=datetime.utcnow()
                    )
                )
                res = db.execute(stmt)
                if res.rowcount == 1:
                    acquired_amb_id = cand.id
                    break
            except Exception:
                db.rollback()
                raise

        if not acquired_amb_id:
            return None

        # 6. Synchronize HospitalQueueItem
        try:
            queue_item = (
                db.query(HospitalQueueItem)
                .filter(HospitalQueueItem.emergency_id == emergency_id)
                .first()
            )
            acquired_amb = db.query(Ambulance).filter(Ambulance.id == acquired_amb_id).one()

            if queue_item:
                queue_item.status = QueueStatusEnum.DISPATCHED
                queue_item.notes = (
                    f"Ambulance {acquired_amb.vehicle_number} ({acquired_amb.driver_name}) dispatched."
                )

            db.commit()
            db.refresh(acquired_amb)
            return AmbulanceDispatchService._to_dispatch_info(db, acquired_amb, emergency_id)

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_location(
        db: Session,
        ambulance_id: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None,
        is_simulated: bool = True,
        timestamp: Optional[datetime] = None
    ) -> Ambulance:
        """
        Ingests GPS or simulated telemetry update for an ambulance.
        Validates latitude (-90 to 90) and longitude (-180 to 180).
        """
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError(f"Invalid latitude {latitude}. Must be between -90.0 and 90.0.")
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Invalid longitude {longitude}. Must be between -180.0 and 180.0.")

        ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
        if not ambulance:
            raise KeyError(f"Ambulance '{ambulance_id}' not found.")

        ambulance.current_latitude = latitude
        ambulance.current_longitude = longitude
        if address:
            ambulance.current_address = address
        ambulance.is_simulated = is_simulated
        ambulance.updated_at = timestamp or datetime.utcnow()
        ambulance.version += 1

        db.commit()
        db.refresh(ambulance)
        return ambulance

    @staticmethod
    def update_route_progress(
        db: Session,
        ambulance_id: str,
        route_progress: float,
        is_simulated: bool = True,
        emergency_id: Optional[str] = None
    ) -> Ambulance:
        """
        Updates journey route progress percentage (0.0 to 100.0).
        Ensures progress does not accidentally move backward during ordinary travel,
        and synchronizes with HospitalQueueItem for Samriddhi's 40% reassignment policy.
        """
        if not (0.0 <= route_progress <= 100.0):
            raise ValueError(f"Invalid route_progress {route_progress}%. Must be between 0.0 and 100.0%.")

        ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
        if not ambulance:
            raise KeyError(f"Ambulance '{ambulance_id}' not found.")

        # Guard against backward progress during ordinary operations
        if route_progress < ambulance.route_progress:
            raise ValueError(
                f"Invalid progress update: route progress cannot move backward from {ambulance.route_progress}% to {route_progress}%."
            )

        # Validate emergency identity if caller supplies emergency_id
        if emergency_id is not None and emergency_id != ambulance.assigned_emergency_id:
            raise ValueError(
                f"Emergency ID mismatch: ambulance '{ambulance_id}' is assigned to "
                f"emergency '{ambulance.assigned_emergency_id}', not '{emergency_id}'."
            )

        ambulance.route_progress = route_progress
        ambulance.is_simulated = is_simulated
        ambulance.updated_at = datetime.utcnow()
        ambulance.version += 1

        # Synchronize with HospitalQueueItem so 40% reassignment policy sees the live route progress!
        active_emg_id = emergency_id or ambulance.assigned_emergency_id
        if active_emg_id:
            queue_item = db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == active_emg_id).first()
            if queue_item:
                queue_item.route_progress = route_progress
                if queue_item.status == QueueStatusEnum.DISPATCHED and route_progress > 0.0:
                    queue_item.status = QueueStatusEnum.EN_ROUTE

        db.commit()
        db.refresh(ambulance)
        return ambulance

    @staticmethod
    def update_status(
        db: Session,
        ambulance_id: str,
        new_status: AmbulanceStatusEnum,
        notes: Optional[str] = None
    ) -> Ambulance:
        """
        Transitions the ambulance through its operational lifecycle state machine.
        Rejects invalid state transitions.
        """
        ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
        if not ambulance:
            raise KeyError(f"Ambulance '{ambulance_id}' not found.")

        allowed = VALID_STATUS_TRANSITIONS.get(ambulance.status, set())
        if new_status != ambulance.status and new_status not in allowed:
            raise ValueError(
                f"Invalid status transition from '{ambulance.status.value}' to '{new_status.value}'."
            )

        # 1. Reject manual AVAILABLE -> ASSIGNED transition (must be initiated via dispatch_for_emergency)
        if ambulance.status == AmbulanceStatusEnum.AVAILABLE and new_status == AmbulanceStatusEnum.ASSIGNED:
            raise ValueError(
                "Cannot manually transition ambulance from 'AVAILABLE' to 'ASSIGNED'. "
                "Ambulance assignment must be initiated through hospital-coordinated dispatch."
            )

        # 2. Require active emergency assignment and destination hospital for active mission stages
        if new_status in {
            AmbulanceStatusEnum.EN_ROUTE_PICKUP,
            AmbulanceStatusEnum.PATIENT_ONBOARD,
            AmbulanceStatusEnum.EN_ROUTE_HOSPITAL,
            AmbulanceStatusEnum.ARRIVED,
        }:
            if not ambulance.assigned_emergency_id or not ambulance.destination_hospital_id:
                raise ValueError(
                    f"Cannot transition to '{new_status.value}' without an active emergency assignment "
                    "and destination hospital."
                )

        ambulance.status = new_status
        ambulance.updated_at = datetime.utcnow()
        ambulance.version += 1

        # Lifecycle synchronization with HospitalQueueItem
        if ambulance.assigned_emergency_id:
            queue_item = (
                db.query(HospitalQueueItem)
                .filter(HospitalQueueItem.emergency_id == ambulance.assigned_emergency_id)
                .first()
            )
            if queue_item:
                if new_status == AmbulanceStatusEnum.ARRIVED:
                    queue_item.status = QueueStatusEnum.ARRIVED
                    queue_item.notes = f"Ambulance {ambulance.vehicle_number} arrived at destination hospital."
                elif new_status == AmbulanceStatusEnum.EN_ROUTE_HOSPITAL:
                    queue_item.status = QueueStatusEnum.EN_ROUTE
                if notes:
                    queue_item.notes = notes

        # When vehicle finishes mission and returns to AVAILABLE, clear emergency links
        if new_status == AmbulanceStatusEnum.AVAILABLE:
            ambulance.assigned_emergency_id = None
            ambulance.destination_hospital_id = None
            ambulance.route_progress = 0.0

        db.commit()
        db.refresh(ambulance)
        return ambulance

    @staticmethod
    def apply_reroute(
        db: Session,
        reroute_event: RerouteEventContract,
        commit: bool = True
    ) -> Optional[Ambulance]:
        """
        Executes reroute on the ambulance assigned to the displaced emergency
        when Samriddhi's bed reassignment policy approves a reassignment (< 40%).
        Updates destination hospital and resets route progress for the new destination path.
        """
        if not reroute_event.newHospitalId:
            return None

        displaced_emg_id = reroute_event.emergencyId
        ambulance = (
            db.query(Ambulance)
            .filter(Ambulance.assigned_emergency_id == displaced_emg_id)
            .first()
        )

        if not ambulance:
            return None

        # Update destination hospital
        ambulance.destination_hospital_id = reroute_event.newHospitalId
        ambulance.status = AmbulanceStatusEnum.EN_ROUTE_HOSPITAL
        # Reset route progress for the new destination branch
        ambulance.route_progress = 0.0
        ambulance.updated_at = datetime.utcnow()
        ambulance.version += 1

        # Synchronize HospitalQueueItem
        queue_item = db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == displaced_emg_id).first()
        if queue_item:
            queue_item.status = QueueStatusEnum.REROUTED
            queue_item.hospital_id = reroute_event.newHospitalId
            queue_item.route_progress = 0.0
            queue_item.notes = f"REROUTED to hospital {reroute_event.newHospitalId} due to priority escalation."

        if commit:
            db.commit()
            db.refresh(ambulance)
        else:
            db.flush()
            db.refresh(ambulance)

        return ambulance

    @staticmethod
    def get_tracking_snapshot(db: Session, emergency_id: str) -> Optional[TrackingSnapshotResponse]:
        """
        Generates a consolidated live tracking state snapshot for a given emergency ID.
        Consumable by patient UI, hospital inbound desk, and Ishita's traffic coordinator.
        """
        ambulance = (
            db.query(Ambulance)
            .filter(Ambulance.assigned_emergency_id == emergency_id)
            .first()
        )
        if not ambulance:
            return None

        hospital_name: Optional[str] = None
        if ambulance.destination_hospital_id:
            hosp = db.query(Hospital).filter(Hospital.id == ambulance.destination_hospital_id).first()
            if hosp:
                hospital_name = hosp.name

        return TrackingSnapshotResponse(
            emergencyId=emergency_id,
            ambulanceId=ambulance.id,
            vehicleNumber=ambulance.vehicle_number,
            driverName=ambulance.driver_name,
            driverContact=ambulance.driver_contact,
            ambulanceType=ambulance.ambulance_type,
            status=ambulance.status,
            currentLocation=CoordinatesContract(
                latitude=ambulance.current_latitude,
                longitude=ambulance.current_longitude,
                address=ambulance.current_address
            ),
            destinationHospitalId=ambulance.destination_hospital_id,
            destinationHospitalName=hospital_name,
            routeProgress=ambulance.route_progress,
            isSimulated=ambulance.is_simulated,
            timestamp=ambulance.updated_at
        )

    @staticmethod
    def _to_dispatch_info(db: Session, ambulance: Ambulance, emergency_id: Optional[str] = None) -> AmbulanceDispatchInfo:
        """Converts an Ambulance database record to an AmbulanceDispatchInfo schema."""
        tags = [t.strip() for t in (ambulance.equipment_tags or "").split(",") if t.strip()]

        dist_km: Optional[float] = None
        if emergency_id:
            emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
            if emergency:
                dist_km = calculate_haversine_distance(
                    emergency.patient_latitude,
                    emergency.patient_longitude,
                    ambulance.current_latitude,
                    ambulance.current_longitude
                )

        return AmbulanceDispatchInfo(
            ambulanceId=ambulance.id,
            vehicleNumber=ambulance.vehicle_number,
            driverName=ambulance.driver_name,
            driverContact=ambulance.driver_contact,
            ambulanceType=ambulance.ambulance_type,
            equipmentTags=tags,
            status=ambulance.status,
            currentLocation=CoordinatesContract(
                latitude=ambulance.current_latitude,
                longitude=ambulance.current_longitude,
                address=ambulance.current_address
            ),
            destinationHospitalId=ambulance.destination_hospital_id,
            routeProgress=ambulance.route_progress,
            estimatedDistanceKm=dist_km,
            assignedAt=ambulance.updated_at
        )

    @staticmethod
    def _to_detail_response(ambulance: Ambulance) -> AmbulanceDetailResponse:
        tags = [t.strip() for t in (ambulance.equipment_tags or "").split(",") if t.strip()]
        return AmbulanceDetailResponse(
            id=ambulance.id,
            vehicleNumber=ambulance.vehicle_number,
            driverName=ambulance.driver_name,
            driverContact=ambulance.driver_contact,
            ambulanceType=ambulance.ambulance_type,
            equipmentTags=tags,
            status=ambulance.status,
            currentLocation=CoordinatesContract(
                latitude=ambulance.current_latitude,
                longitude=ambulance.current_longitude,
                address=ambulance.current_address
            ),
            assignedEmergencyId=ambulance.assigned_emergency_id,
            destinationHospitalId=ambulance.destination_hospital_id,
            routeProgress=ambulance.route_progress,
            isSimulated=ambulance.is_simulated,
            version=ambulance.version,
            updatedAt=ambulance.updated_at
        )
