import uuid
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import update
from backend.config import settings
from backend.models.bed import Bed
from backend.models.reservation import BedReservation
from backend.models.queue import HospitalQueueItem
from backend.models.emergency import Emergency
from backend.models.audit import ReassignmentAuditLog
from backend.models.enums import BedStatusEnum, ReservationStatusEnum, PriorityEnum, BedTypeEnum, QueueStatusEnum
from backend.schemas.reassignment import (
    ReassignmentEvaluationRequest,
    ReassignmentEvaluationResponse,
)
from backend.schemas.reservation import BedReservationDetail
from backend.schemas.ranking import RankingRequest
from backend.services.ranking_service import HospitalRankingEngine
from backend.services.bed_service import BedManagementService
from backend.shared.contracts import RerouteEventContract, EVENT_BED_REASSIGNMENT_REROUTE

# Priority Rank ordering (Lower numerical value = higher clinical urgency)
PRIORITY_RANK = {
    PriorityEnum.P1_CRITICAL: 1,
    PriorityEnum.P2_EMERGENCY: 2,
    PriorityEnum.P3_URGENT: 3,
    PriorityEnum.P4_NON_URGENT: 4,
}

class BedReassignmentService:
    """
    Priority-based Bed Reassignment Engine implementing the configurable
    40% route-progress prototype policy.
    
    PROTOTYPE POLICY DISCLAIMER:
    This policy is a configurable demonstration rule for prototype coordination.
    It does not constitute a clinical, medical, legal, or scientifically validated protocol.
    """

    @staticmethod
    def evaluate_and_reassign(
        db: Session,
        request: ReassignmentEvaluationRequest,
        ranking_engine: Optional[HospitalRankingEngine] = None
    ) -> ReassignmentEvaluationResponse:
        """
        Evaluates whether a newly arriving higher-priority emergency can reassign a currently
        reserved bed at the target hospital based on the 40% route-progress prototype policy.
        """
        if ranking_engine is None:
            ranking_engine = HospitalRankingEngine()

        threshold = settings.REASSIGNMENT_ROUTE_THRESHOLD_PERCENT
        target_hospital_id = request.targetHospitalId
        req_bed_type = request.requiredBedType
        displacing_priority = request.displacingPriority

        # Step 1: Check if an available bed already exists without needing reassignment
        available_bed = (
            db.query(Bed)
            .filter(
                Bed.hospital_id == target_hospital_id,
                Bed.bed_type == req_bed_type,
                Bed.status == BedStatusEnum.AVAILABLE
            )
            .first()
        )

        if available_bed:
            # Bed is freely available; standard reservation applies
            res, bed = BedManagementService.reserve_bed_atomically(
                db=db,
                hospital_id=target_hospital_id,
                bed_type=req_bed_type,
                emergency_id=request.displacingEmergencyId,
                specific_bed_id=available_bed.id
            )
            return ReassignmentEvaluationResponse(
                decision="DIRECT_RESERVATION",
                reason=f"An available {req_bed_type.value} bed was found without requiring reassignment.",
                thresholdPercent=threshold,
                displacingReservation=BedReservationDetail(
                    reservationId=res.id,
                    bedId=bed.id,
                    bedNumber=bed.bed_number,
                    bedType=bed.bed_type,
                    status=res.status,
                    reservedAt=res.reserved_at
                )
            )

        # Step 2: Contention exists! Find active reservations for this bed type at the hospital
        active_reservations = (
            db.query(BedReservation)
            .join(Bed, BedReservation.bed_id == Bed.id)
            .filter(
                BedReservation.hospital_id == target_hospital_id,
                Bed.bed_type == req_bed_type,
                BedReservation.status == ReservationStatusEnum.RESERVED
            )
            .all()
        )

        if not active_reservations:
            return ReassignmentEvaluationResponse(
                decision="REASSIGNMENT_REJECTED",
                reason=f"No active reservations for {req_bed_type.value} found to evaluate.",
                thresholdPercent=threshold
            )

        # Find candidates holding reservations with lower priority than displacing emergency
        displacing_rank = PRIORITY_RANK[displacing_priority]
        reassignable_candidates = []

        for res in active_reservations:
            queue_item = (
                db.query(HospitalQueueItem)
                .filter(HospitalQueueItem.emergency_id == res.emergency_id)
                .first()
            )
            if not queue_item:
                continue

            current_rank = PRIORITY_RANK.get(queue_item.priority, 5)
            # Reassignment candidate must have LOWER priority (higher numerical rank)
            if current_rank > displacing_rank:
                reassignable_candidates.append((res, queue_item))

        if not reassignable_candidates:
            # All active reservations are of equal or higher priority
            event_id = f"evt-audit-{uuid.uuid4().hex[:8]}"
            audit_log = ReassignmentAuditLog(
                id=f"audit-{uuid.uuid4().hex[:8]}",
                event_id=event_id,
                displaced_emergency_id="NONE",
                displacing_emergency_id=request.displacingEmergencyId,
                displaced_priority=displacing_priority,
                displacing_priority=displacing_priority,
                previous_hospital_id=target_hospital_id,
                previous_bed_id="NONE",
                route_progress=0.0,
                threshold=threshold,
                decision="REASSIGNMENT_REJECTED",
                reason="No active reservation holds a lower priority than incoming emergency.",
                created_at=datetime.utcnow()
            )
            db.add(audit_log)
            db.commit()

            return ReassignmentEvaluationResponse(
                decision="REASSIGNMENT_REJECTED",
                reason="All active bed reservations at target hospital are equal or higher priority.",
                thresholdPercent=threshold
            )

        # Pick the lowest priority candidate (highest rank number)
        # In case of tie, pick the one with lowest route progress
        reassignable_candidates.sort(
            key=lambda x: (PRIORITY_RANK.get(x[1].priority, 5), -x[1].route_progress),
            reverse=True
        )
        target_res, target_queue = reassignable_candidates[0]
        displaced_emg_id = target_res.emergency_id
        route_progress = target_queue.route_progress

        # Step 3: Evaluate 40% route-progress prototype policy threshold
        if route_progress >= threshold:
            # Policy rule: Ambulance has covered >= 40% of its journey; reservation is retained!
            event_id = f"evt-audit-{uuid.uuid4().hex[:8]}"
            reason_msg = (
                f"Active reservation retained: ambulance has covered {route_progress}% of route "
                f"(>= configurable prototype threshold of {threshold}%)."
            )
            audit_log = ReassignmentAuditLog(
                id=f"audit-{uuid.uuid4().hex[:8]}",
                event_id=event_id,
                displaced_emergency_id=displaced_emg_id,
                displacing_emergency_id=request.displacingEmergencyId,
                displaced_priority=target_queue.priority,
                displacing_priority=displacing_priority,
                previous_hospital_id=target_hospital_id,
                previous_bed_id=target_res.bed_id,
                route_progress=route_progress,
                threshold=threshold,
                decision="REASSIGNMENT_REJECTED",
                reason=reason_msg,
                created_at=datetime.utcnow()
            )
            db.add(audit_log)
            db.commit()

            return ReassignmentEvaluationResponse(
                decision="REASSIGNMENT_REJECTED",
                reason=reason_msg,
                thresholdPercent=threshold,
                displacedEmergencyId=displaced_emg_id,
                routeProgress=route_progress
            )

        # Step 4: Policy approval: route_progress < 40.0% -> Execute Reassignment!
        event_id = f"evt-reassign-{uuid.uuid4().hex[:8]}"
        reassigned_bed_id = target_res.bed_id

        # 4a. Update displaced reservation status
        target_res.status = ReservationStatusEnum.RELEASED_FOR_REASSIGNMENT
        target_res.released_at = datetime.utcnow()
        target_res.reassigned_to_emergency_id = request.displacingEmergencyId

        # Ensure displacing emergency entity exists in database
        displacing_emergency = db.query(Emergency).filter(Emergency.id == request.displacingEmergencyId).first()
        if not displacing_emergency:
            displacing_emergency = Emergency(
                id=request.displacingEmergencyId,
                patient_id=f"pat-{uuid.uuid4().hex[:6]}",
                emergency_type="HIGH_PRIORITY_ESCALATION",
                priority=displacing_priority,
                patient_latitude=request.patientLocation.latitude,
                patient_longitude=request.patientLocation.longitude,
                patient_address=request.patientLocation.address,
                required_bed_type=req_bed_type,
                selected_hospital_id=target_hospital_id
            )
            db.add(displacing_emergency)
            db.flush()
        else:
            displacing_emergency.selected_hospital_id = target_hospital_id
            db.flush()

        # 4b. Allocate the bed to displacing emergency
        new_res_id = f"res-{uuid.uuid4().hex[:8]}"
        displacing_res = BedReservation(
            id=new_res_id,
            emergency_id=request.displacingEmergencyId,
            hospital_id=target_hospital_id,
            bed_id=reassigned_bed_id,
            status=ReservationStatusEnum.RESERVED,
            reserved_at=datetime.utcnow()
        )
        db.add(displacing_res)

        # 4c. Update Queue for displacing emergency
        displacing_queue = (
            db.query(HospitalQueueItem)
            .filter(HospitalQueueItem.emergency_id == request.displacingEmergencyId)
            .first()
        )
        if not displacing_queue:
            displacing_queue = HospitalQueueItem(
                id=f"qitem-{uuid.uuid4().hex[:8]}",
                hospital_id=target_hospital_id,
                emergency_id=request.displacingEmergencyId,
                priority=displacing_priority,
                status=QueueStatusEnum.COORDINATING,
                route_progress=0.0,
                notes=f"Reassigned bed {reassigned_bed_id} due to higher priority."
            )
            db.add(displacing_queue)
        else:
            displacing_queue.hospital_id = target_hospital_id
            displacing_queue.status = QueueStatusEnum.COORDINATING

        # 4d. Mark displaced queue item as REROUTED
        target_queue.status = QueueStatusEnum.REROUTED
        target_queue.notes = f"Displaced by higher priority emergency {request.displacingEmergencyId}."

        # 4e. Find next best ranked hospital for the displaced emergency
        displaced_emergency = db.query(Emergency).filter(Emergency.id == displaced_emg_id).first()
        next_best_hospital = None
        next_best_hospital_id = None
        next_best_bed_id = None

        if displaced_emergency:
            # Query ranking engine for alternative hospitals excluding the contention hospital
            rank_req = RankingRequest(
                emergencyId=displaced_emg_id,
                patientLocation=request.patientLocation,
                emergencyType=displaced_emergency.emergency_type,
                priority=displaced_emergency.priority,
                requiredBedType=displaced_emergency.required_bed_type,
                requiredCapabilities=[]
            )
            rank_resp = ranking_engine.rank_hospitals(db, rank_req)
            # Find next eligible hospital
            for cand in rank_resp.rankedHospitals:
                if cand.hospitalId != target_hospital_id and cand.isEligible:
                    next_best_hospital = {
                        "hospitalId": cand.hospitalId,
                        "name": cand.name,
                        "distanceKm": cand.breakdown.distanceKm,
                        "availableBeds": cand.breakdown.availableBedsCount
                    }
                    next_best_hospital_id = cand.hospitalId
                    break

        # 4f. Construct machine-readable rerouting event for Nidhi's module
        reroute_event = RerouteEventContract(
            eventType=EVENT_BED_REASSIGNMENT_REROUTE,
            eventId=event_id,
            emergencyId=displaced_emg_id,
            previousHospitalId=target_hospital_id,
            previousBedId=reassigned_bed_id,
            newHospitalId=next_best_hospital_id,
            newBedId=next_best_bed_id,
            displacingEmergencyId=request.displacingEmergencyId,
            displacingPriority=displacing_priority,
            displacedPriority=target_queue.priority,
            reason="HIGHER_PRIORITY_EMERGENCY",
            routeProgress=route_progress,
            threshold=threshold,
            status="REROUTE_REQUIRED",
            timestamp=datetime.utcnow()
        )

        # 4g. Persist ReassignmentAuditLog
        audit_log = ReassignmentAuditLog(
            id=f"audit-{uuid.uuid4().hex[:8]}",
            event_id=event_id,
            displaced_emergency_id=displaced_emg_id,
            displacing_emergency_id=request.displacingEmergencyId,
            displaced_priority=target_queue.priority,
            displacing_priority=displacing_priority,
            previous_hospital_id=target_hospital_id,
            previous_bed_id=reassigned_bed_id,
            new_hospital_id=next_best_hospital_id,
            new_bed_id=next_best_bed_id,
            route_progress=route_progress,
            threshold=threshold,
            decision="REASSIGNMENT_APPROVED",
            reason=f"Priority escalation: {displacing_priority.value} displaced {target_queue.priority.value} at {route_progress}% route progress (< {threshold}% threshold).",
            created_at=datetime.utcnow()
        )
        db.add(audit_log)

        # Commit all changes in a single atomic transaction
        db.commit()

        # Fetch locked bed details
        bed_obj = db.query(Bed).filter(Bed.id == reassigned_bed_id).one()

        return ReassignmentEvaluationResponse(
            decision="REASSIGNMENT_APPROVED",
            reason=audit_log.reason,
            thresholdPercent=threshold,
            displacedEmergencyId=displaced_emg_id,
            routeProgress=route_progress,
            displacingReservation=BedReservationDetail(
                reservationId=displacing_res.id,
                bedId=bed_obj.id,
                bedNumber=bed_obj.bed_number,
                bedType=bed_obj.bed_type,
                status=displacing_res.status,
                reservedAt=displacing_res.reserved_at
            ),
            rerouteEvent=reroute_event,
            nextBestHospital=next_best_hospital
        )
