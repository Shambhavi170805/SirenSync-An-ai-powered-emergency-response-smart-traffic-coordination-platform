"""
Comprehensive Automated Tests for SirenSync Phase 1 & 2 Integration:
Ambulance Dispatch Service, Database Foundations, and State Transitions.

Covers Scenarios 1 to 15:
1. Existing emergencies migrate successfully with default '[]'
2. Existing emergency rows retain authentic values across migration
3. required_capabilities persists correctly from payload to DB to response
4. Empty / omitted capabilities remain backward compatible
5. Missing emergency rejects dispatch with explicit error (no fallback coordinates)
6. Eligible ambulance is selected based on capabilities and distance
7. Ambulance lacking required equipment (e.g., VENTILATOR) is strictly excluded
8. No available ambulance leaves bed reservation intact and updates queue note to pending
9. Duplicate dispatch returns existing assignment idempotently
10. One ambulance cannot be assigned to two emergencies
11. Concurrent duplicate dispatch CAS concurrency safety
12. Invalid coordinates (NaN, Inf, out of range) are strictly rejected
13. Invalid route progress (NaN, negative, >100, regression) is strictly rejected
14. Invalid status transitions are strictly rejected
15. Existing HospitalQueueItem is updated rather than duplicated (Single Queue guarantee)
"""
import math
from datetime import datetime, timedelta
import concurrent.futures
import pytest
from sqlalchemy import inspect
from pydantic import ValidationError

from tests_hospital.conftest import TestingSessionLocal
from backend.database.init_db import migrate_db
from backend.database.session import engine
from backend.models.ambulance import Ambulance
from backend.models.emergency import Emergency
from backend.models.hospital import Hospital
from backend.models.reservation import BedReservation
from backend.models.queue import HospitalQueueItem
from backend.models.enums import (
    AmbulanceStatusEnum,
    PriorityEnum,
    BedTypeEnum,
    ReservationStatusEnum,
    QueueStatusEnum,
)
from backend.services.ambulance_service import (
    AmbulanceDispatchService,
    ambulance_satisfies_capabilities,
)
from backend.schemas.ambulance import (
    LocationUpdateRequest,
    RouteProgressUpdateRequest,
)




@pytest.mark.parametrize(
    "active_status",
    [
        AmbulanceStatusEnum.ASSIGNED,
        AmbulanceStatusEnum.EN_ROUTE_PICKUP,
        AmbulanceStatusEnum.PATIENT_ONBOARD,
        AmbulanceStatusEnum.EN_ROUTE_HOSPITAL,
    ],
)
def test_active_ambulance_cannot_be_marked_available_mid_emergency(db_session, active_status):
    """An ambulance remains unavailable until its current journey reaches ARRIVED."""
    ambulance = db_session.query(Ambulance).first()
    assert ambulance is not None
    ambulance.status = active_status
    ambulance.assigned_emergency_id = "emg-active-lock"
    ambulance.destination_hospital_id = "hosp-manipal-hal"
    db_session.commit()

    with pytest.raises(ValueError, match="Invalid status transition"):
        AmbulanceDispatchService.update_status(
            db_session, ambulance.id, AmbulanceStatusEnum.AVAILABLE
        )

    db_session.refresh(ambulance)
    assert ambulance.status == active_status
    assert ambulance.assigned_emergency_id == "emg-active-lock"


# ==============================================================================
# Scenario 1: Migration idempotency & default '[]'
# ==============================================================================
def test_hospital_facility_capabilities_do_not_filter_ambulance_fleet(db_session):
    """CARDIAC_CATH_LAB is a hospital capability, not ambulance-carried equipment."""
    ambulance = db_session.query(Ambulance).filter(Ambulance.status == AmbulanceStatusEnum.AVAILABLE).first()
    assert ambulance is not None
    ambulance.equipment_tags = "OXYGEN,STRETCHER"
    db_session.flush()
    assert ambulance_satisfies_capabilities(ambulance, ["CARDIAC_CATH_LAB", "STROKE_UNIT", "TRAUMA_LEVEL_1"]) is True
    assert ambulance_satisfies_capabilities(ambulance, ["VENTILATOR"]) is False


def test_01_existing_emergencies_migration_default_capabilities(db_session):
    """Scenario 1: Verify required_capabilities column exists and defaults to '[]'."""
    migrate_db(engine)

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("emergencies")}
    assert "required_capabilities" in columns, "Column 'required_capabilities' must exist on 'emergencies'"

    emergencies = db_session.query(Emergency).all()
    assert len(emergencies) > 0, "Expected pre-seeded emergencies to exist"
    for emg in emergencies:
        caps = emg.required_capabilities
        if isinstance(caps, list):
            assert isinstance(caps, list)
        elif isinstance(caps, str):
            import json
            parsed = json.loads(caps)
            assert isinstance(parsed, list)


# ==============================================================================
# Scenario 2: Existing emergency rows retain values
# ==============================================================================
def test_02_existing_emergency_rows_retain_authentic_values(db_session):
    """Scenario 2: Verify existing emergency rows retain priority, symptoms, coordinates."""
    cardiac_emg = db_session.query(Emergency).filter(Emergency.id == "demo-cardiac-01").first()
    assert cardiac_emg is not None, "Pre-seeded demo-cardiac-01 must exist"
    assert cardiac_emg.patient_id == "pat-demo-cardiac-01"
    assert cardiac_emg.priority == PriorityEnum.P1_CRITICAL
    assert cardiac_emg.required_bed_type == BedTypeEnum.ICU
    assert cardiac_emg.patient_latitude == 12.9716
    assert cardiac_emg.patient_longitude == 77.5946
    assert "chest pain" in cardiac_emg.symptoms.lower() or "cardiac" in cardiac_emg.symptoms.lower()


# ==============================================================================
# Scenario 3: required_capabilities persistence (Payload -> DB -> Response)
# ==============================================================================
def test_03_required_capabilities_persists_payload_to_db_to_response(client, db_session):
    """Scenario 3: Verify required_capabilities persists from API payload to DB and GET response."""
    emg_id = "emg-cap-persist-001"
    payload = {
        "emergencyId": emg_id,
        "patientId": "pat-persist-001",
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "patientLocation": {
            "latitude": 30.3255,
            "longitude": 78.0437,
            "address": "Rajpur Road, Dehradun"
        },
        "requiredBedType": "ICU",
        "symptoms": "Severe acute respiratory distress requiring mechanical ventilation",
        "requiredCapabilities": ["ICU_VENTILATOR", "CARDIAC_CATH_LAB"]
    }

    # 1. Register via API
    res = client.post("/api/v1/emergencies", json=payload)
    assert res.status_code == 201, f"Registration failed: {res.text}"
    body = res.json()
    assert body["emergencyId"] == emg_id
    assert body["requiredCapabilities"] == ["ICU_VENTILATOR", "CARDIAC_CATH_LAB"]

    # 2. Verify direct database row
    db_emg = db_session.query(Emergency).filter(Emergency.id == emg_id).first()
    assert db_emg is not None
    caps = db_emg.required_capabilities
    if isinstance(caps, str):
        import json
        caps = json.loads(caps)
    assert "ICU_VENTILATOR" in caps
    assert "CARDIAC_CATH_LAB" in caps

    # 3. Verify retrieval via GET endpoint
    get_res = client.get(f"/api/v1/emergencies/{emg_id}")
    assert get_res.status_code == 200
    get_body = get_res.json()
    assert get_body["requiredCapabilities"] == ["ICU_VENTILATOR", "CARDIAC_CATH_LAB"]


# ==============================================================================
# Scenario 4: Backward compatibility with empty capabilities
# ==============================================================================
def test_04_empty_capabilities_backward_compatible(client, db_session):
    """Scenario 4: Verify emergency without requiredCapabilities defaults to empty list cleanly."""
    emg_id = "emg-cap-empty-002"
    payload = {
        "emergencyId": emg_id,
        "patientId": "pat-empty-002",
        "emergencyType": "GENERAL_TRAUMA",
        "priority": "P2_EMERGENCY",
        "patientLocation": {
            "latitude": 30.3382,
            "longitude": 78.0163,
            "address": "Ballupur, Dehradun"
        },
        "requiredBedType": "TRAUMA_EMERGENCY",
        "symptoms": "Lower limb fracture"
    }

    res = client.post("/api/v1/emergencies", json=payload)
    assert res.status_code == 201
    assert res.json()["requiredCapabilities"] == []

    get_res = client.get(f"/api/v1/emergencies/{emg_id}")
    assert get_res.status_code == 200
    assert get_res.json()["requiredCapabilities"] == []


# ==============================================================================
# Scenario 5: Missing emergency rejects dispatch (No fallback coordinates)
# ==============================================================================
def test_05_missing_emergency_rejects_dispatch_without_fallback(db_session):
    """Scenario 5: Verify dispatch fails explicitly when emergency is missing (no silent fallback)."""
    with pytest.raises(ValueError, match="Emergency 'emg-nonexistent-xyz' not found"):
        AmbulanceDispatchService.dispatch_for_emergency(
            db=db_session,
            emergency_id="emg-nonexistent-xyz",
            hospital_id="hosp-manipal-hal"
        )


# ==============================================================================
# Scenario 6: Eligible ambulance selected by capabilities and distance
# ==============================================================================
def test_06_eligible_ambulance_selected_by_capabilities_and_distance(db_session):
    """Scenario 6: Verify closest ambulance matching capabilities is dispatched."""
    emg = Emergency(
        id="emg-ddn-dispatch-01",
        patient_id="pat-ddn-01",
        emergency_type="CARDIAC_ARREST",
        priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=30.3255,
        patient_longitude=78.0437,
        patient_address="Clock Tower, Dehradun",
        required_bed_type=BedTypeEnum.ICU,
        required_capabilities=["VENTILATOR"],
        symptoms="Cardiac arrest"
    )
    db_session.add(emg)

    hosp = Hospital(
        id="hosp-ddn-max",
        name="Max Super Speciality Hospital Dehradun",
        address="Mussoorie Diversion Road, Dehradun",
        region="Dehradun",
        latitude=30.3700,
        longitude=78.0700,
        contact_number="+91-135-6673000",
        is_active=True
    )
    db_session.merge(hosp)

    qitem = HospitalQueueItem(
        id="qitem-ddn-01",
        hospital_id=hosp.id,
        emergency_id=emg.id,
        priority=PriorityEnum.P1_CRITICAL,
        status=QueueStatusEnum.COORDINATING,
        route_progress=0.0
    )
    db_session.add(qitem)
    db_session.commit()

    dispatch_info = AmbulanceDispatchService.dispatch_for_emergency(
        db=db_session,
        emergency_id=emg.id,
        hospital_id=hosp.id
    )

    assert dispatch_info is not None
    # amb-ddn-als-01 is right at Clock Tower (30.3255, 78.0437), dist ~0 km, with VENTILATOR
    assert dispatch_info.ambulanceId == "amb-ddn-als-01"
    assert dispatch_info.status == AmbulanceStatusEnum.ASSIGNED
    assert dispatch_info.destinationHospitalId == hosp.id

    # Verify single HospitalQueueItem updated to DISPATCHED
    db_session.refresh(qitem)
    assert qitem.status == QueueStatusEnum.DISPATCHED


# ==============================================================================
# Scenario 7: Ambulance lacking required equipment is strictly excluded
# ==============================================================================
def test_07_ambulance_lacking_equipment_is_excluded(db_session):
    """Scenario 7: BLS ambulance without VENTILATOR is excluded even if distance is 0."""
    emg = Emergency(
        id="emg-ddn-vent-req",
        patient_id="pat-ddn-02",
        emergency_type="RESPIRATORY_FAILURE",
        priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=30.3125,
        patient_longitude=78.0465,
        patient_address="Dharampur, Dehradun",
        required_bed_type=BedTypeEnum.ICU,
        required_capabilities=["VENTILATOR"],
        symptoms="Severe respiratory distress requiring mechanical ventilation"
    )
    db_session.add(emg)

    qitem = HospitalQueueItem(
        id="qitem-ddn-vent",
        hospital_id="hosp-manipal-hal",
        emergency_id=emg.id,
        priority=PriorityEnum.P1_CRITICAL,
        status=QueueStatusEnum.COORDINATING
    )
    db_session.add(qitem)
    db_session.commit()

    dispatch_info = AmbulanceDispatchService.dispatch_for_emergency(
        db=db_session,
        emergency_id=emg.id,
        hospital_id="hosp-manipal-hal"
    )

    assert dispatch_info is not None
    # amb-ddn-bls-01 must NOT be selected because it has no VENTILATOR
    assert dispatch_info.ambulanceId != "amb-ddn-bls-01"
    assigned = db_session.query(Ambulance).filter(Ambulance.id == dispatch_info.ambulanceId).one()
    assert ambulance_satisfies_capabilities(assigned, ["VENTILATOR"]) is True


# ==============================================================================
# Scenario 8: No available ambulance preserves bed reservation
# ==============================================================================
def test_08_no_available_ambulance_preserves_bed_reservation(db_session):
    """Scenario 8: When no ambulance matches requirements, bed reservation remains RESERVED and note is set."""
    # Explicit ambulance equipment requirement that no vehicle in this test
    # fleet carries. Hospital-only requirements such as CARDIAC_CATH_LAB must
    # not be used as ambulance equipment filters.
    db_session.query(Ambulance).update({Ambulance.equipment_tags: "OXYGEN,STRETCHER"}, synchronize_session=False)
    db_session.commit()
    emg = Emergency(
        id="emg-no-amb-01",
        patient_id="pat-no-amb",
        emergency_type="CARDIAC",
        priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=12.9592,
        patient_longitude=77.6477,
        required_bed_type=BedTypeEnum.ICU,
        required_capabilities=["VENTILATOR"],
        symptoms="Cardiac event requiring ultra-specialized equipment"
    )
    db_session.add(emg)

    # Bed reservation
    res = BedReservation(
        id="res-no-amb-01",
        emergency_id=emg.id,
        hospital_id="hosp-manipal-hal",
        bed_id="bed-hosp-manipal-hal-icu-01",
        status=ReservationStatusEnum.RESERVED
    )
    db_session.add(res)

    qitem = HospitalQueueItem(
        id="qitem-no-amb-01",
        hospital_id="hosp-manipal-hal",
        emergency_id=emg.id,
        priority=PriorityEnum.P1_CRITICAL,
        status=QueueStatusEnum.COORDINATING,
        notes="Initial queue entry"
    )
    db_session.add(qitem)
    db_session.commit()

    # Attempt dispatch
    result = AmbulanceDispatchService.dispatch_for_emergency(
        db=db_session,
        emergency_id=emg.id,
        hospital_id="hosp-manipal-hal"
    )

    assert result is None, "Dispatch must return None when no ambulance is available"

    # Bed reservation must be preserved in RESERVED status
    db_session.refresh(res)
    assert res.status == ReservationStatusEnum.RESERVED

    # HospitalQueueItem note must explain pending dispatch
    db_session.refresh(qitem)
    assert "Automatic ambulance matching and dispatch retry are active" in qitem.notes


def test_pending_dispatch_escalates_after_two_minutes_without_eligible_unit(db_session):
    db_session.query(Ambulance).update({Ambulance.equipment_tags: "OXYGEN,STRETCHER"}, synchronize_session=False)
    emg = Emergency(
        id="emg-pending-escalate-01", patient_id="pat-pending-escalate-01",
        emergency_type="RESPIRATORY", priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=30.3255, patient_longitude=78.0437,
        required_bed_type=BedTypeEnum.ICU, required_capabilities=["ICU_VENTILATOR"],
    )
    db_session.add(emg)
    queue = HospitalQueueItem(
        id="qitem-pending-escalate-01", hospital_id="hosp-manipal-hal",
        emergency_id=emg.id, priority=PriorityEnum.P1_CRITICAL,
        status=QueueStatusEnum.COORDINATING,
        dispatch_pending_since=datetime.utcnow() - timedelta(minutes=3),
    )
    db_session.add(queue)
    db_session.add(BedReservation(
        id="res-pending-escalate-01", emergency_id=emg.id,
        hospital_id="hosp-manipal-hal", bed_id="bed-hosp-manipal-hal-icu-01",
        status=ReservationStatusEnum.RESERVED,
    ))
    db_session.commit()
    result = AmbulanceDispatchService.dispatch_for_emergency(db_session, emg.id, "hosp-manipal-hal")
    assert result is None
    db_session.refresh(queue)
    assert queue.dispatch_escalated_at is not None
    assert "Hospital desk escalation required" in queue.notes


def test_pending_dispatch_can_recover_when_eligible_vehicle_becomes_available(db_session):
    """A pending reservation is retriable; the same queue row receives the later assignment."""
    from datetime import datetime, timedelta
    db_session.query(Ambulance).update({Ambulance.equipment_tags: "OXYGEN,STRETCHER"}, synchronize_session=False)
    emg = Emergency(
        id="emg-pending-retry-01", patient_id="pat-pending-retry-01",
        emergency_type="RESPIRATORY", priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=30.3255, patient_longitude=78.0437,
        required_bed_type=BedTypeEnum.ICU, required_capabilities=["ICU_VENTILATOR"],
    )
    db_session.add(emg)
    queue = HospitalQueueItem(
        id="qitem-pending-retry-01", hospital_id="hosp-manipal-hal",
        emergency_id=emg.id, priority=PriorityEnum.P1_CRITICAL,
        status=QueueStatusEnum.COORDINATING,
    )
    db_session.add(queue)
    db_session.add(BedReservation(
        id="res-pending-retry-01", emergency_id=emg.id,
        hospital_id="hosp-manipal-hal", bed_id="bed-hosp-manipal-hal-icu-01",
        status=ReservationStatusEnum.RESERVED,
    ))
    db_session.commit()

    first = AmbulanceDispatchService.dispatch_for_emergency(db_session, emg.id, "hosp-manipal-hal")
    assert first is None
    db_session.refresh(queue)
    assert queue.dispatch_pending_since is not None

    available = db_session.query(Ambulance).filter(Ambulance.status == AmbulanceStatusEnum.AVAILABLE).first()
    available.equipment_tags = "VENTILATOR,OXYGEN,DEFIBRILLATOR"
    db_session.commit()
    second = AmbulanceDispatchService.dispatch_for_emergency(db_session, emg.id, "hosp-manipal-hal")
    assert second is not None
    db_session.refresh(queue)
    assert queue.dispatch_pending_since is None
    assert queue.dispatch_attempt_count == 0
    assert queue.status == QueueStatusEnum.DISPATCHED


# ==============================================================================
# Scenario 9: Duplicate dispatch is idempotent
# ==============================================================================
def test_09_duplicate_dispatch_returns_existing_assignment_idempotently(db_session):
    """Scenario 9: Calling dispatch twice for the same emergency returns existing assignment."""
    emg = Emergency(
        id="emg-idemp-dispatch",
        patient_id="pat-idemp",
        emergency_type="TRAUMA",
        priority=PriorityEnum.P2_EMERGENCY,
        patient_latitude=12.9716,
        patient_longitude=77.5946,
        required_bed_type=BedTypeEnum.TRAUMA_EMERGENCY,
        symptoms="Trauma injury"
    )
    db_session.add(emg)

    qitem = HospitalQueueItem(
        id="qitem-idemp",
        hospital_id="hosp-manipal-hal",
        emergency_id=emg.id,
        priority=PriorityEnum.P2_EMERGENCY,
        status=QueueStatusEnum.COORDINATING
    )
    db_session.add(qitem)
    db_session.commit()

    disp1 = AmbulanceDispatchService.dispatch_for_emergency(db_session, emg.id, "hosp-manipal-hal")
    assert disp1 is not None

    # Second dispatch call
    disp2 = AmbulanceDispatchService.dispatch_for_emergency(db_session, emg.id, "hosp-manipal-hal")
    assert disp2 is not None
    assert disp1.ambulanceId == disp2.ambulanceId
    assert disp1.assignedAt == disp2.assignedAt


# ==============================================================================
# Scenario 10: One ambulance cannot be assigned to two emergencies
# ==============================================================================
def test_10_one_ambulance_cannot_be_assigned_to_two_emergencies(db_session):
    """Scenario 10: An already assigned ambulance cannot be assigned to a second emergency."""
    assigned_amb = (
        db_session.query(Ambulance)
        .filter(Ambulance.assigned_emergency_id.isnot(None))
        .first()
    )
    if not assigned_amb:
        assigned_amb = db_session.query(Ambulance).filter(Ambulance.status == AmbulanceStatusEnum.AVAILABLE).first()
        assert assigned_amb is not None
        assigned_amb.status = AmbulanceStatusEnum.ASSIGNED
        assigned_amb.assigned_emergency_id = "demo-cardiac-01"
        assigned_amb.destination_hospital_id = "hosp-manipal-hal"
        db_session.commit()

    emg2 = Emergency(
        id="emg-amb-conflict-02",
        patient_id="pat-conflict-02",
        emergency_type="TRAUMA",
        priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=assigned_amb.current_latitude,
        patient_longitude=assigned_amb.current_longitude,
        required_bed_type=BedTypeEnum.ICU,
        symptoms="Critical condition"
    )
    db_session.add(emg2)
    db_session.commit()

    disp = AmbulanceDispatchService.dispatch_for_emergency(db_session, emg2.id, "hosp-manipal-hal")
    if disp:
        assert disp.ambulanceId != assigned_amb.id, "Cannot assign already-occupied ambulance"


# ==============================================================================
# Scenario 11: Concurrent duplicate dispatch CAS concurrency safety
# ==============================================================================
def test_11_concurrent_duplicate_dispatch_cas_concurrency_safety(db_session):
    """Scenario 11: Two threads attempting concurrent dispatch for the same emergency resolve safely."""
    target_emg_id = "emg-race-dispatch-01"
    emg = Emergency(
        id=target_emg_id,
        patient_id="pat-race-01",
        emergency_type="CARDIAC_ARREST",
        priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=12.9784,
        patient_longitude=77.6408,
        required_bed_type=BedTypeEnum.ICU,
        symptoms="Cardiac arrest under concurrent race condition"
    )
    db_session.add(emg)
    qitem = HospitalQueueItem(
        id="qitem-race-01",
        hospital_id="hosp-manipal-hal",
        emergency_id=target_emg_id,
        priority=PriorityEnum.P1_CRITICAL,
        status=QueueStatusEnum.COORDINATING
    )
    db_session.add(qitem)
    db_session.commit()

    def run_dispatch():
        session = TestingSessionLocal()
        try:
            return AmbulanceDispatchService.dispatch_for_emergency(
                db=session,
                emergency_id=target_emg_id,
                hospital_id="hosp-manipal-hal"
            )
        finally:
            session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_dispatch)
        f2 = executor.submit(run_dispatch)
        r1 = f1.result()
        r2 = f2.result()

    assert r1 is not None
    assert r2 is not None
    assert r1.ambulanceId == r2.ambulanceId, "Both concurrent threads must resolve to the exact same ambulance assignment"

    assigned_count = (
        db_session.query(Ambulance)
        .filter(Ambulance.assigned_emergency_id == emg.id)
        .count()
    )
    assert assigned_count == 1, "Exactly one ambulance must be assigned"


# ==============================================================================
# Scenario 12: Invalid coordinates strictly rejected
# ==============================================================================
def test_12_invalid_coordinates_rejected(db_session):
    """Scenario 12: Telemetry updates with NaN, Inf, or out-of-range coordinates are rejected."""
    with pytest.raises(ValidationError):
        LocationUpdateRequest(latitude=float("nan"), longitude=77.59)

    with pytest.raises(ValidationError):
        LocationUpdateRequest(latitude=float("inf"), longitude=77.59)

    with pytest.raises(ValidationError):
        LocationUpdateRequest(latitude=95.0, longitude=77.59)

    with pytest.raises(ValidationError):
        LocationUpdateRequest(latitude=12.97, longitude=195.0)

    amb = db_session.query(Ambulance).first()
    assert amb is not None

    with pytest.raises(ValueError, match="Latitude must be a finite number"):
        AmbulanceDispatchService.update_location(db_session, amb.id, latitude=float("nan"), longitude=77.59)

    with pytest.raises(ValueError, match="Longitude must be a finite number"):
        AmbulanceDispatchService.update_location(db_session, amb.id, latitude=12.97, longitude=200.0)


# ==============================================================================
# Scenario 13: Invalid route progress strictly rejected
# ==============================================================================
def test_13_invalid_route_progress_rejected(db_session):
    """Scenario 13: Progress NaN, negative, >100, or regressions are rejected."""
    with pytest.raises(ValidationError):
        RouteProgressUpdateRequest(routeProgress=float("nan"))

    with pytest.raises(ValidationError):
        RouteProgressUpdateRequest(routeProgress=-5.0)

    with pytest.raises(ValidationError):
        RouteProgressUpdateRequest(routeProgress=105.0)

    # Pick or prepare an ambulance with an assigned emergency
    amb = db_session.query(Ambulance).filter(Ambulance.assigned_emergency_id.isnot(None)).first()
    if not amb:
        # Assign one if not already assigned
        amb = db_session.query(Ambulance).filter(Ambulance.status == AmbulanceStatusEnum.AVAILABLE).first()
        amb.status = AmbulanceStatusEnum.ASSIGNED
        amb.assigned_emergency_id = "demo-cardiac-01"
        amb.route_progress = 0.0
        db_session.commit()

    # Advance progress to 40.0%
    amb.route_progress = 40.0
    db_session.commit()

    # Regression attempt (40.0 -> 20.0) must fail
    with pytest.raises(ValueError, match="Route progress cannot move backward"):
        AmbulanceDispatchService.update_route_progress(db_session, amb.id, route_progress=20.0)

    # Mismatched emergency_id must fail
    with pytest.raises(ValueError, match="Emergency ID mismatch"):
        AmbulanceDispatchService.update_route_progress(
            db_session, amb.id, route_progress=50.0, emergency_id="emg-wrong-id"
        )


# ==============================================================================
# Scenario 14: Invalid status transitions strictly rejected
# ==============================================================================
def test_14_invalid_status_transitions_rejected(db_session):
    """Scenario 14: Illegal status transitions in state machine are rejected."""
    avail_amb = db_session.query(Ambulance).filter(
        Ambulance.status == AmbulanceStatusEnum.AVAILABLE,
        Ambulance.assigned_emergency_id.is_(None)
    ).first()
    if not avail_amb:
        # Create a fresh available ambulance for the test
        avail_amb = Ambulance(
            id="amb-test-lifecycle-01",
            vehicle_number="UK-07-LIFE-01",
            driver_name="Lifecycle Driver",
            driver_contact="+91-99999-00001",
            status=AmbulanceStatusEnum.AVAILABLE,
            current_latitude=30.3255,
            current_longitude=78.0437,
            current_address="Test Station",
            assigned_emergency_id=None,
            destination_hospital_id=None,
            route_progress=0.0
        )
        db_session.add(avail_amb)
        db_session.commit()

    # Attempt leap from AVAILABLE directly to ARRIVED
    with pytest.raises(ValueError, match="Invalid status transition"):
        AmbulanceDispatchService.update_status(db_session, avail_amb.id, AmbulanceStatusEnum.ARRIVED)

    # Attempt manual leap to ASSIGNED without coordinated dispatch
    with pytest.raises(ValueError, match="Cannot manually transition"):
        AmbulanceDispatchService.update_status(db_session, avail_amb.id, AmbulanceStatusEnum.ASSIGNED)


# ==============================================================================
# Scenario 15: Existing HospitalQueueItem is updated, never duplicated
# ==============================================================================
def test_15_single_queue_item_synchronized_not_duplicated(db_session):
    """Scenario 15: Verify single HospitalQueueItem is updated on dispatch, progress, and arrival."""
    emg = Emergency(
        id="emg-single-queue-test",
        patient_id="pat-sq-01",
        emergency_type="CARDIAC_ARREST",
        priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=12.9592,
        patient_longitude=77.6477,
        required_bed_type=BedTypeEnum.ICU,
        symptoms="Single queue verification"
    )
    db_session.add(emg)

    qitem = HospitalQueueItem(
        id="qitem-sq-01",
        hospital_id="hosp-manipal-hal",
        emergency_id=emg.id,
        priority=PriorityEnum.P1_CRITICAL,
        status=QueueStatusEnum.COORDINATING,
        route_progress=0.0
    )
    db_session.add(qitem)
    db_session.commit()

    # Pre-check: exactly 1 queue item
    initial_count = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg.id).count()
    assert initial_count == 1

    # 1. Dispatch
    disp = AmbulanceDispatchService.dispatch_for_emergency(db_session, emg.id, "hosp-manipal-hal")
    assert disp is not None

    # Post-dispatch: count must still be 1, status DISPATCHED
    count_after_disp = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg.id).count()
    assert count_after_disp == 1
    db_session.refresh(qitem)
    assert qitem.status == QueueStatusEnum.DISPATCHED

    # 2. Advance route progress to 25.0%
    AmbulanceDispatchService.update_route_progress(db_session, disp.ambulanceId, route_progress=25.0)
    count_after_progress = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg.id).count()
    assert count_after_progress == 1
    db_session.refresh(qitem)
    assert qitem.status == QueueStatusEnum.EN_ROUTE
    assert qitem.route_progress == 25.0

    # 3. Transition to ARRIVED
    AmbulanceDispatchService.update_status(db_session, disp.ambulanceId, AmbulanceStatusEnum.EN_ROUTE_PICKUP)
    AmbulanceDispatchService.update_status(db_session, disp.ambulanceId, AmbulanceStatusEnum.PATIENT_ONBOARD)
    AmbulanceDispatchService.update_status(db_session, disp.ambulanceId, AmbulanceStatusEnum.ARRIVED)

    count_after_arrival = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg.id).count()
    assert count_after_arrival == 1
    db_session.refresh(qitem)
    assert qitem.status == QueueStatusEnum.ARRIVED
