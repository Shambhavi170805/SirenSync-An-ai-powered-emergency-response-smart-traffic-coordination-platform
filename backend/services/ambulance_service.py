import math
from typing import Optional, List, Dict, Set, Any
from datetime import datetime
import json
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
    AmbulanceStatusEnum.ASSIGNED: {AmbulanceStatusEnum.EN_ROUTE_PICKUP, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.EN_ROUTE_PICKUP: {AmbulanceStatusEnum.PATIENT_ONBOARD, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.PATIENT_ONBOARD: {AmbulanceStatusEnum.EN_ROUTE_HOSPITAL, AmbulanceStatusEnum.ARRIVED, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.EN_ROUTE_HOSPITAL: {AmbulanceStatusEnum.ARRIVED, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.ARRIVED: {AmbulanceStatusEnum.AVAILABLE, AmbulanceStatusEnum.MAINTENANCE},
    AmbulanceStatusEnum.MAINTENANCE: {AmbulanceStatusEnum.AVAILABLE},
}

# Clinical capability to equipment tag mapping aliases
CAPABILITY_EQUIPMENT_MAP: Dict[str, Set[str]] = {
    "VENTILATOR": {"VENTILATOR", "FULL_ICU_VENTILATOR", "ICU_VENTILATOR"},
    "ICU_VENTILATOR": {"VENTILATOR", "FULL_ICU_VENTILATOR", "ICU_VENTILATOR"},
    "DEFIBRILLATOR": {"DEFIBRILLATOR"},
    "OXYGEN": {"OXYGEN", "OXYGEN_CYLINDER"},
    "ECG": {"ECG", "MULTIPARA_MONITOR"},
    "INFUSION_PUMP": {"INFUSION_PUMP"},
    "MULTIPARA_MONITOR": {"MULTIPARA_MONITOR"},
    "STRETCHER": {"STRETCHER"},
    "FIRST_AID_KIT": {"FIRST_AID_KIT"},
}

def ambulance_satisfies_capabilities(ambulance: Ambulance, required_caps: List[str]) -> bool:
    """
    Evaluates whether an ambulance carries all required clinical equipment.
    Treats required capabilities as hard eligibility constraints.
    """
    if not required_caps:
        return True

    amb_tags = set(t.strip().upper() for t in (ambulance.equipment_tags or "").split(",") if t.strip())

    # `Emergency.required_capabilities` is primarily the hospital-capability
    # contract used by ranking (e.g. CARDIAC_CATH_LAB, STROKE_UNIT,
    # TRAUMA_LEVEL_1, OXYGEN_HDU). Those are facility capabilities, not
    # equipment that can physically be carried by an ambulance. Only explicit
    # ambulance equipment requirements are hard-filtered here. This prevents
    # every otherwise suitable ambulance being rejected for lacking a cath lab.
    for req in required_caps:
        if not req or not isinstance(req, str):
            continue
        req_norm = req.strip().upper()
        mapped_tags = CAPABILITY_EQUIPMENT_MAP.get(req_norm)
        if mapped_tags is None:
            # Not an ambulance-equipment capability. Hospital ranking remains
            # responsible for evaluating this requirement.
            continue
        if req_norm in amb_tags or any(req_norm in tag for tag in amb_tags):
            continue
        if amb_tags.intersection(mapped_tags):
            continue
        return False

    return True


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
        Enforces atomic compare-and-swap, hard capability matching, and single queue coordination.
        """
        # 1. Idempotency Check: if ambulance already assigned to this emergency, return existing
        existing_assignment = (
            db.query(Ambulance)
            .filter(Ambulance.assigned_emergency_id == emergency_id)
            .first()
        )
        if existing_assignment:
            return AmbulanceDispatchService._to_dispatch_info(db, existing_assignment, emergency_id)

        # 2. Strict Emergency Validation: Reject dispatch if emergency does not exist
        emergency = db.query(Emergency).filter(Emergency.id == emergency_id).first()
        if not emergency:
            raise ValueError(f"Cannot dispatch ambulance: Emergency '{emergency_id}' not found.")
        if emergency.patient_latitude is None or emergency.patient_longitude is None:
            raise ValueError(f"Cannot dispatch ambulance: Emergency '{emergency_id}' has no valid coordinates.")

        p_lat = emergency.patient_latitude
        p_lng = emergency.patient_longitude
        priority = emergency.priority

        # 3. Hospital Validation
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise ValueError(f"Cannot dispatch ambulance: Hospital '{hospital_id}' not found.")

        # Extract required capabilities from emergency entity
        raw_caps = emergency.required_capabilities or []
        if isinstance(raw_caps, str):
            try:
                raw_caps = json.loads(raw_caps)
            except Exception:
                raw_caps = []

        # 4. Query AVAILABLE unassigned ambulances
        candidates = (
            db.query(Ambulance)
            .filter(
                Ambulance.status == AmbulanceStatusEnum.AVAILABLE,
                Ambulance.assigned_emergency_id.is_(None)
            )
            .all()
        )

        # Hard Eligibility Filter: Ambulance must satisfy all clinical capabilities
        eligible_candidates = [
            amb for amb in candidates
            if ambulance_satisfies_capabilities(amb, raw_caps)
        ]

        if not eligible_candidates:
            # A concurrent request may have acquired the last eligible ambulance
            # after our initial idempotency check. Re-read the assignment before
            # reporting a pending dispatch so duplicate callers resolve identically.
            db.expire_all()
            concurrent_assignment = (
                db.query(Ambulance)
                .filter(Ambulance.assigned_emergency_id == emergency_id)
                .first()
            )
            if concurrent_assignment:
                return AmbulanceDispatchService._to_dispatch_info(
                    db, concurrent_assignment, emergency_id
                )

            # Safe no-ambulance behavior: retain the bed reservation and update
            # the existing HospitalQueueItem only.
            qitem = db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emergency_id).first()
            if qitem:
                now = datetime.utcnow()
                if qitem.dispatch_pending_since is None:
                    qitem.dispatch_pending_since = now
                qitem.dispatch_attempt_count = int(qitem.dispatch_attempt_count or 0) + 1
                if qitem.dispatch_escalated_at is not None:
                    qitem.notes = "Dispatch delayed over 2 min. Hospital desk escalation required; automatic retry continues."
                elif (now - qitem.dispatch_pending_since).total_seconds() >= 120:
                    qitem.dispatch_escalated_at = now
                    qitem.notes = "Dispatch delayed over 2 min. Hospital desk escalation required; automatic retry continues."
                else:
                    qitem.notes = "Bed reserved. Automatic ambulance matching and dispatch retry are active."
                db.commit()
            return None

        # 5. Score and sort candidates by type preference and geographic distance
        def candidate_sort_key(amb: Ambulance):
            type_score = 0
            if priority == PriorityEnum.P1_CRITICAL:
                if amb.ambulance_type in (AmbulanceTypeEnum.MICU, AmbulanceTypeEnum.ALS):
                    type_score = -2
            elif priority == PriorityEnum.P2_EMERGENCY:
                if amb.ambulance_type in (AmbulanceTypeEnum.ALS, AmbulanceTypeEnum.BLS):
                    type_score = -1

            dist_km = calculate_haversine_distance(
                p_lat, p_lng, amb.current_latitude, amb.current_longitude
            )
            return (type_score, dist_km)

        eligible_candidates.sort(key=candidate_sort_key)

        # 6. Atomic Compare-and-Swap (CAS) assignment
        acquired_amb_id: Optional[str] = None
        for cand in eligible_candidates:
            # Re-check race condition: did another thread assign an ambulance to this emergency?
            race_check = (
                db.query(Ambulance)
                .filter(Ambulance.assigned_emergency_id == emergency_id)
                .first()
            )
            if race_check:
                return AmbulanceDispatchService._to_dispatch_info(db, race_check, emergency_id)

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
                race_check = (
                    db.query(Ambulance)
                    .filter(Ambulance.assigned_emergency_id == emergency_id)
                    .first()
                )
                if race_check:
                    return AmbulanceDispatchService._to_dispatch_info(db, race_check, emergency_id)
                raise

        if not acquired_amb_id:
            # Re-check after failed CAS attempts. Another worker may have won the
            # race for this same emergency while this session was evaluating candidates.
            db.expire_all()
            concurrent_assignment = (
                db.query(Ambulance)
                .filter(Ambulance.assigned_emergency_id == emergency_id)
                .first()
            )
            if concurrent_assignment:
                return AmbulanceDispatchService._to_dispatch_info(
                    db, concurrent_assignment, emergency_id
                )

            qitem = db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emergency_id).first()
            if qitem:
                now = datetime.utcnow()
                if qitem.dispatch_pending_since is None:
                    qitem.dispatch_pending_since = now
                qitem.dispatch_attempt_count = int(qitem.dispatch_attempt_count or 0) + 1
                if qitem.dispatch_escalated_at is not None:
                    qitem.notes = "Dispatch delayed over 2 min. Hospital desk escalation required; automatic retry continues."
                elif (now - qitem.dispatch_pending_since).total_seconds() >= 120:
                    qitem.dispatch_escalated_at = now
                    qitem.notes = "Dispatch delayed over 2 min. Hospital desk escalation required; automatic retry continues."
                else:
                    qitem.notes = "Bed reserved. Automatic ambulance matching and dispatch retry are active."
                db.commit()
            return None

        # 7. Synchronize existing HospitalQueueItem
        acquired_amb = db.query(Ambulance).filter(Ambulance.id == acquired_amb_id).one()
        queue_item = (
            db.query(HospitalQueueItem)
            .filter(HospitalQueueItem.emergency_id == emergency_id)
            .first()
        )
        if queue_item:
            queue_item.status = QueueStatusEnum.DISPATCHED
            queue_item.notes = (
                f"Ambulance {acquired_amb.vehicle_number} ({acquired_amb.driver_name}) dispatched."
            )
            queue_item.dispatch_pending_since = None
            queue_item.dispatch_attempt_count = 0
            queue_item.dispatch_escalated_at = None
            queue_item.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(acquired_amb)

        return AmbulanceDispatchService._to_dispatch_info(db, acquired_amb, emergency_id)

    @staticmethod
    def update_location(
        db: Session,
        ambulance_id: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None,
        is_simulated: bool = True,
        timestamp: Optional[datetime] = None,
        route_progress: Optional[float] = None
    ) -> Ambulance:
        """
        Updates live or simulated GPS telemetry for an ambulance.
        Validates latitude and longitude within finite WGS84 boundaries.
        """
        if not math.isfinite(latitude) or latitude < -90.0 or latitude > 90.0:
            raise ValueError(f"Latitude must be a finite number between -90 and 90 (received: {latitude})")
        if not math.isfinite(longitude) or longitude < -180.0 or longitude > 180.0:
            raise ValueError(f"Longitude must be a finite number between -180 and 180 (received: {longitude})")

        ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
        if not ambulance:
            raise KeyError(f"Ambulance '{ambulance_id}' not found.")

        ambulance.current_latitude = latitude
        ambulance.current_longitude = longitude
        if address:
            ambulance.current_address = address
        ambulance.is_simulated = is_simulated
        if route_progress is not None:
            if not math.isfinite(route_progress) or route_progress < 0.0 or route_progress > 100.0:
                raise ValueError("GPS-derived route progress must be between 0 and 100.")
            if route_progress + 0.25 < float(ambulance.route_progress or 0.0):
                # Ignore small GPS jitter; route progress is monotonic on a route.
                route_progress = float(ambulance.route_progress or 0.0)
            ambulance.route_progress = max(float(ambulance.route_progress or 0.0), route_progress)
        if not is_simulated and ambulance.status == AmbulanceStatusEnum.ASSIGNED:
            ambulance.status = AmbulanceStatusEnum.EN_ROUTE_PICKUP
        ambulance.updated_at = timestamp or datetime.utcnow()
        ambulance.version += 1

        if ambulance.assigned_emergency_id:
            queue_item = db.query(HospitalQueueItem).filter(
                HospitalQueueItem.emergency_id == ambulance.assigned_emergency_id
            ).first()
            if queue_item:
                queue_item.route_progress = float(ambulance.route_progress or 0.0)
                if queue_item.route_progress > 0 and queue_item.status in {QueueStatusEnum.DISPATCHED, QueueStatusEnum.COORDINATING}:
                    queue_item.status = QueueStatusEnum.EN_ROUTE
                    queue_item.notes = f"Ambulance {ambulance.vehicle_number} is en route; GPS telemetry active."

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
        Updates route progress percentage (0.0 to 100.0).
        Enforces monotonic progression on the same route and synchronizes with HospitalQueueItem.
        """
        if not math.isfinite(route_progress) or route_progress < 0.0 or route_progress > 100.0:
            raise ValueError(f"Route progress must be a finite number between 0.0 and 100.0 (received: {route_progress})")

        ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
        if not ambulance:
            raise KeyError(f"Ambulance '{ambulance_id}' not found.")

        # Guard against emergency ID mismatch
        if emergency_id is not None and emergency_id != ambulance.assigned_emergency_id:
            raise ValueError(
                f"Emergency ID mismatch: ambulance '{ambulance_id}' is assigned to "
                f"emergency '{ambulance.assigned_emergency_id}', not '{emergency_id}'."
            )

        # Monotonicity check: route progress cannot regress on the active journey
        if route_progress < ambulance.route_progress:
            raise ValueError(
                f"Route progress cannot move backward (current: {ambulance.route_progress:.1f}%, target: {route_progress:.1f}%)."
            )

        ambulance.route_progress = route_progress
        ambulance.is_simulated = is_simulated
        ambulance.updated_at = datetime.utcnow()
        ambulance.version += 1

        # Synchronize with HospitalQueueItem so reassignment policy sees the live route progress
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
        Transitions the ambulance through its validated operational lifecycle state machine.
        Rejects invalid state leaps and synchronizes the single HospitalQueueItem.
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

        # Lifecycle synchronization with single HospitalQueueItem
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
        Updates destination hospital, resets route progress to 0.0 for the new destination path,
        and updates the single HospitalQueueItem.
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

        # Synchronize existing HospitalQueueItem
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
    def build_reroute_payload(reroute_event: RerouteEventContract, ambulance: Optional[Ambulance] = None) -> Dict[str, Any]:
        """Constructs broadcast payload for REROUTE_ALERT notifications."""
        return {
            "eventId": str(reroute_event.eventId),
            "emergencyId": str(reroute_event.emergencyId),
            "ambulanceId": ambulance.id if ambulance else "UNKNOWN",
            "vehicleNumber": ambulance.vehicle_number if ambulance else "UNKNOWN",
            "previousHospitalId": str(reroute_event.previousHospitalId),
            "newHospitalId": str(reroute_event.newHospitalId),
            "displacingEmergencyId": str(reroute_event.displacingEmergencyId),
            "displacingPriority": (
                reroute_event.displacingPriority.value
                if hasattr(reroute_event.displacingPriority, "value")
                else str(reroute_event.displacingPriority)
            ),
            "displacedPriority": (
                reroute_event.displacedPriority.value
                if hasattr(reroute_event.displacedPriority, "value")
                else str(reroute_event.displacedPriority)
            ),
            "reason": str(reroute_event.reason),
            "routeProgress": float(ambulance.route_progress) if ambulance else 0.0,
            "status": "REROUTE_EXECUTED",
            "timestamp": (
                reroute_event.timestamp.isoformat()
                if hasattr(reroute_event.timestamp, "isoformat")
                else str(reroute_event.timestamp)
            )
        }

    @staticmethod
    def get_tracking_snapshot(db: Session, emergency_id: str) -> Optional[TrackingSnapshotResponse]:
        """
        Generates a consolidated live tracking state snapshot for a given emergency ID.
        Consumable by patient UI, hospital inbound desk, and driver console.
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
            try:
                coords = (
                    db.query(Emergency.patient_latitude, Emergency.patient_longitude)
                    .filter(Emergency.id == emergency_id)
                    .first()
                )
                if coords and coords[0] is not None and coords[1] is not None:
                    dist_km = calculate_haversine_distance(
                        float(coords[0]),
                        float(coords[1]),
                        float(ambulance.current_latitude),
                        float(ambulance.current_longitude)
                    )
            except Exception:
                dist_km = None

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
