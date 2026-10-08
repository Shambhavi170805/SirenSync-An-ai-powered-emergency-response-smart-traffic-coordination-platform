import uuid
from backend.services.bed_service import BedManagementService
from backend.services.reassignment_service import BedReassignmentService
from backend.models.enums import BedTypeEnum, BedStatusEnum, PriorityEnum, ReservationStatusEnum, QueueStatusEnum
from backend.models.queue import HospitalQueueItem
from backend.models.bed import Bed
from backend.models.hospital import Hospital
from backend.models.emergency import Emergency
from backend.schemas.reassignment import ReassignmentEvaluationRequest
from backend.shared.contracts import CoordinatesContract, EVENT_BED_REASSIGNMENT_REROUTE

def test_reassignment_approved_below_40_percent_progress(db_session):
    """
    Scenario C: Priority escalation causes reassignment when route progress < 40%.
    Displaced emergency (P3) ambulance has covered 25% of route.
    Incoming emergency (P1) requires the same bed.
    Policy rule (25% < 40%) approves reassignment and issues rerouting event.
    """
    # 1. Setup hospital with 0 available beds and 1 active P3 reservation
    hosp_id = f"hosp-reassign-c-{uuid.uuid4().hex[:6]}"
    bed_id = f"bed-reassign-c-{uuid.uuid4().hex[:6]}"
    displaced_emg_id = f"emg-displaced-{uuid.uuid4().hex[:6]}"
    displacing_emg_id = f"emg-displacing-{uuid.uuid4().hex[:6]}"

    hosp = Hospital(
        id=hosp_id,
        name="Policy Validation Hospital C",
        address="Test Corridor C, Bangalore",
        latitude=12.9500,
        longitude=77.6000,
        contact_number="+91-80-1234-5678",
        is_active=True
    )
    db_session.add(hosp)
    db_session.flush()

    bed = Bed(
        id=bed_id,
        hospital_id=hosp_id,
        bed_number="ICU-REASSIGN-01",
        bed_type=BedTypeEnum.ICU,
        status=BedStatusEnum.AVAILABLE,
        department="Critical Care"
    )
    db_session.add(bed)
    db_session.commit()

    # Create initial reservation for P3 emergency
    res, _ = BedManagementService.reserve_bed_atomically(
        db=db_session,
        hospital_id=hosp_id,
        bed_type=BedTypeEnum.ICU,
        emergency_id=displaced_emg_id,
        specific_bed_id=bed_id
    )

    # Set route progress to 25.0% (< 40.0% threshold) and priority to P3_URGENT
    queue_item = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == displaced_emg_id).one()
    queue_item.priority = PriorityEnum.P3_URGENT
    queue_item.route_progress = 25.0
    queue_item.status = QueueStatusEnum.EN_ROUTE

    displaced_emg = db_session.query(Emergency).filter(Emergency.id == displaced_emg_id).one()
    displaced_emg.priority = PriorityEnum.P3_URGENT
    db_session.commit()

    # 2. Evaluate reassignment for incoming P1_CRITICAL emergency
    req = ReassignmentEvaluationRequest(
        displacingEmergencyId=displacing_emg_id,
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId=hosp_id,
        patientLocation=CoordinatesContract(latitude=12.9600, longitude=77.6100)
    )

    eval_response = BedReassignmentService.evaluate_and_reassign(db_session, req)

    # 3. Assertions
    assert eval_response.decision == "REASSIGNMENT_APPROVED"
    assert eval_response.displacedEmergencyId == displaced_emg_id
    assert eval_response.routeProgress == 25.0
    assert eval_response.thresholdPercent == 40.0

    # Rerouting event must be generated and valid
    reroute_evt = eval_response.rerouteEvent
    assert reroute_evt is not None
    assert reroute_evt.eventType == EVENT_BED_REASSIGNMENT_REROUTE
    assert reroute_evt.emergencyId == displaced_emg_id
    assert reroute_evt.previousHospitalId == hosp_id
    assert reroute_evt.previousBedId == bed_id
    assert reroute_evt.routeProgress == 25.0
    assert reroute_evt.threshold == 40.0
    assert reroute_evt.status == "REROUTE_REQUIRED"

    # Database state verification
    db_session.refresh(res)
    assert res.status == ReservationStatusEnum.RELEASED_FOR_REASSIGNMENT
    assert res.reassigned_to_emergency_id == displacing_emg_id

    # Queue status updated
    db_session.refresh(queue_item)
    assert queue_item.status == QueueStatusEnum.REROUTED

def test_reassignment_rejected_above_40_percent_progress(db_session):
    """
    Scenario D: Reassignment rejected when route progress >= 40%.
    Displaced emergency (P3) ambulance has covered 65% of route.
    Incoming emergency (P1) arrives.
    Policy rule (65% >= 40%) preserves existing reservation to maintain coordination stability.
    """
    hosp_id = f"hosp-reassign-d-{uuid.uuid4().hex[:6]}"
    bed_id = f"bed-reassign-d-{uuid.uuid4().hex[:6]}"
    displaced_emg_id = f"emg-displaced-d-{uuid.uuid4().hex[:6]}"
    displacing_emg_id = f"emg-displacing-d-{uuid.uuid4().hex[:6]}"

    hosp = Hospital(
        id=hosp_id,
        name="Policy Validation Hospital D",
        address="Test Corridor D, Bangalore",
        latitude=12.9500,
        longitude=77.6000,
        contact_number="+91-80-1234-5678",
        is_active=True
    )
    db_session.add(hosp)
    db_session.flush()

    bed = Bed(
        id=bed_id,
        hospital_id=hosp_id,
        bed_number="ICU-REASSIGN-D01",
        bed_type=BedTypeEnum.ICU,
        status=BedStatusEnum.AVAILABLE,
        department="Critical Care"
    )
    db_session.add(bed)
    db_session.commit()

    res, _ = BedManagementService.reserve_bed_atomically(
        db=db_session,
        hospital_id=hosp_id,
        bed_type=BedTypeEnum.ICU,
        emergency_id=displaced_emg_id,
        specific_bed_id=bed_id
    )

    # Route progress is 65% (>= 40% threshold)
    queue_item = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == displaced_emg_id).one()
    queue_item.priority = PriorityEnum.P3_URGENT
    queue_item.route_progress = 65.0
    queue_item.status = QueueStatusEnum.EN_ROUTE

    displaced_emg = db_session.query(Emergency).filter(Emergency.id == displaced_emg_id).one()
    displaced_emg.priority = PriorityEnum.P3_URGENT
    db_session.commit()

    req = ReassignmentEvaluationRequest(
        displacingEmergencyId=displacing_emg_id,
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId=hosp_id,
        patientLocation=CoordinatesContract(latitude=12.9600, longitude=77.6100)
    )

    eval_response = BedReassignmentService.evaluate_and_reassign(db_session, req)

    # Reassignment must be rejected
    assert eval_response.decision == "REASSIGNMENT_REJECTED"
    assert "65.0%" in eval_response.reason
    assert "40.0%" in eval_response.reason
    assert eval_response.rerouteEvent is None

    # Original reservation must be strictly preserved
    db_session.refresh(res)
    assert res.status == ReservationStatusEnum.RESERVED

def test_reassignment_rejected_for_equal_or_lower_priority(db_session):
    """
    Reassignment must be rejected if the incoming emergency is equal or lower priority.
    """
    hosp_id = f"hosp-reassign-low-{uuid.uuid4().hex[:6]}"
    bed_id = f"bed-reassign-low-{uuid.uuid4().hex[:6]}"
    holder_emg_id = f"emg-holder-{uuid.uuid4().hex[:6]}"

    hosp = Hospital(
        id=hosp_id,
        name="Policy Low Priority Hospital",
        address="Test Corridor, Bangalore",
        latitude=12.9500,
        longitude=77.6000,
        contact_number="+91-80-0000-1111",
        is_active=True
    )
    db_session.add(hosp)
    db_session.flush()

    bed = Bed(
        id=bed_id,
        hospital_id=hosp_id,
        bed_number="ICU-LOW-01",
        bed_type=BedTypeEnum.ICU,
        status=BedStatusEnum.AVAILABLE,
        department="Critical Care"
    )
    db_session.add(bed)
    db_session.commit()

    BedManagementService.reserve_bed_atomically(
        db=db_session,
        hospital_id=hosp_id,
        bed_type=BedTypeEnum.ICU,
        emergency_id=holder_emg_id,
        specific_bed_id=bed_id
    )

    # Existing holder is P2_EMERGENCY at 10% progress
    qitem = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == holder_emg_id).one()
    qitem.priority = PriorityEnum.P2_EMERGENCY
    qitem.route_progress = 10.0
    db_session.commit()

    # Incoming request is lower priority: P3_URGENT
    req = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-incoming-p3",
        displacingPriority=PriorityEnum.P3_URGENT,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId=hosp_id,
        patientLocation=CoordinatesContract(latitude=12.9600, longitude=77.6100)
    )

    res = BedReassignmentService.evaluate_and_reassign(db_session, req)
    assert res.decision == "REASSIGNMENT_REJECTED"
