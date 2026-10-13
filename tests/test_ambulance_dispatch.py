"""
Tests for Phase 2: Hospital-Coordinated Ambulance Dispatch & Hook
Verifies that:
1. Ambulance assignment is triggered only after hospital selection and bed reservation succeed.
2. Only eligible AVAILABLE ambulances are assigned.
3. Concurrency-safe atomic locking prevents double-assignment.
4. Dispatch is idempotent on retry.
5. If no ambulance is available, bed reservation is preserved and honest status is returned.
"""
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy.orm import Session

from backend.models.ambulance import Ambulance
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum, PriorityEnum, BedTypeEnum
from backend.models.emergency import Emergency
from backend.models.bed import Bed
from backend.models.hospital import Hospital
from backend.services.ambulance_service import AmbulanceDispatchService
from backend.services.bed_service import BedManagementService
from seed.demo_seed_data import AMBULANCES_DATA

@pytest.fixture(autouse=True)
def clean_ambulance_fleet_state(db_session: Session):
    """
    Guarantees that each dispatch test runs against a clean ambulance fleet
    and prevents mutations from leaking to subsequent test modules.
    """
    pre_test_ids = {a.id for a in db_session.query(Ambulance.id).all()}

    yield

    # Restore all seeded ambulances to their authoritative baseline from AMBULANCES_DATA
    for amb_data in AMBULANCES_DATA:
        amb = db_session.get(Ambulance, amb_data["id"])
        if amb:
            amb.status = amb_data["status"]
            amb.assigned_emergency_id = amb_data["assigned_emergency_id"]
            amb.destination_hospital_id = amb_data["destination_hospital_id"]
            amb.route_progress = amb_data["route_progress"]

    # Delete only temporary ambulances created within this specific test
    created_ambs = (
        db_session.query(Ambulance)
        .filter(~Ambulance.id.in_(pre_test_ids))
        .all()
    )
    for extra in created_ambs:
        db_session.delete(extra)

    db_session.commit()

def test_dispatch_after_successful_hospital_selection(client):
    """
    Verifies end-to-end hospital selection hook dispatches an ambulance
    after atomic bed locking succeeds.
    """
    emergency_id = f"emg-dispatch-e2e-{uuid.uuid4().hex[:6]}"
    top_hospital_id = "hosp-manipal-hal"

    # Select hospital and reserve ICU bed
    select_payload = {
        "selectedHospitalId": top_hospital_id,
        "requiredBedType": "ICU"
    }
    r_select = client.post(f"/api/v1/emergencies/{emergency_id}/select-hospital", json=select_payload)
    assert r_select.status_code == 201
    data = r_select.json()

    # 1. Bed reservation succeeded
    assert data["status"] == "SUCCESS"
    assert data["reservation"]["status"] == "RESERVED"
    assert data["coordinatingHospital"]["dispatchStatus"] == "AMBULANCE_COORDINATION_INITIATED"

    # 2. Ambulance dispatch succeeded and attached
    assert data["assignedAmbulance"] is not None
    amb_info = data["assignedAmbulance"]
    assert amb_info["ambulanceId"] is not None
    assert amb_info["status"] == "ASSIGNED"
    assert amb_info["destinationHospitalId"] == top_hospital_id
    assert amb_info["routeProgress"] == 0.0

def test_dispatch_idempotency(db_session: Session):
    """
    Verifies that calling dispatch multiple times for the same emergency
    returns the existing assignment without creating duplicates or reassigning.
    """
    emg_id = f"emg-idempotent-{uuid.uuid4().hex[:6]}"
    hosp_id = "hosp-manipal-hal"

    # Pre-create valid Emergency record for relational integrity
    emg = Emergency(
        id=emg_id,
        patient_id=f"pat-idemp-{uuid.uuid4().hex[:6]}",
        emergency_type="ACUTE_CARDIO_RESPIRATORY",
        priority=PriorityEnum.P2_EMERGENCY,
        patient_latitude=12.9716,
        patient_longitude=77.5946,
        required_bed_type=BedTypeEnum.ICU,
        selected_hospital_id=hosp_id
    )
    db_session.add(emg)
    db_session.commit()

    # First dispatch call
    first_res = AmbulanceDispatchService.dispatch_for_emergency(
        db=db_session,
        emergency_id=emg_id,
        hospital_id=hosp_id
    )
    assert first_res is not None
    assigned_id = first_res.ambulanceId

    # Second dispatch call with same emergency_id
    second_res = AmbulanceDispatchService.dispatch_for_emergency(
        db=db_session,
        emergency_id=emg_id,
        hospital_id=hosp_id
    )
    assert second_res is not None
    # Must return identical ambulance ID
    assert second_res.ambulanceId == assigned_id

    # Verify database still only has 1 ambulance linked to this emergency
    assigned_count = (
        db_session.query(Ambulance)
        .filter(Ambulance.assigned_emergency_id == emg_id)
        .count()
    )
    assert assigned_count == 1

def test_no_ambulance_available_preserves_bed_reservation(client, db_session: Session):
    """
    Verifies that if no ambulance is available:
    - Bed reservation STILL succeeds.
    - assignedAmbulance is None (honest reporting).
    - dispatchStatus reports AMBULANCE_PENDING_AVAILABILITY.
    - Reservation is NOT rolled back.
    """
    # Mark all ambulances as MAINTENANCE so none are AVAILABLE
    db_session.query(Ambulance).update({"status": AmbulanceStatusEnum.MAINTENANCE})
    db_session.commit()

    emg_id = f"emg-no-amb-{uuid.uuid4().hex[:6]}"
    select_payload = {
        "selectedHospitalId": "hosp-apollo-bg",
        "requiredBedType": "OXYGEN_HDU"
    }

    resp = client.post(f"/api/v1/emergencies/{emg_id}/select-hospital", json=select_payload)
    assert resp.status_code == 201
    data = resp.json()

    # Bed reservation remains intact
    assert data["status"] == "SUCCESS"
    assert data["reservation"]["status"] == "RESERVED"

    # Honest ambulance status: none assigned
    assert data["assignedAmbulance"] is None
    assert data["coordinatingHospital"]["dispatchStatus"] == "AMBULANCE_PENDING_AVAILABILITY"
    assert "no ambulance is currently available" in data["message"].lower()

def test_concurrency_race_condition_zero_double_assignment(db_session: Session):
    """
    Multi-threaded concurrency test:
    10 concurrent threads attempt to dispatch for 10 distinct emergencies,
    competing for exactly 1 AVAILABLE ambulance.
    Asserts:
    - Exactly 1 thread successfully locks the ambulance.
    - 9 threads receive None.
    - Zero double-assignments occur in the database.
    """
    # Create an isolated candidate ambulance with unique ID
    amb_id = f"amb-race-test-{uuid.uuid4().hex[:6]}"
    test_amb = Ambulance(
        id=amb_id,
        vehicle_number=f"KA-RACE-{uuid.uuid4().hex[:4].upper()}",
        driver_name="Race Test Driver",
        driver_contact="+91-99999-11111",
        ambulance_type=AmbulanceTypeEnum.ALS,
        equipment_tags="VENTILATOR,OXYGEN",
        status=AmbulanceStatusEnum.AVAILABLE,
        current_latitude=12.9716,
        current_longitude=77.5946,
        current_address="Race Test Stand",
        assigned_emergency_id=None,
        destination_hospital_id=None,
        route_progress=0.0,
        version=1
    )
    db_session.add(test_amb)
    # Set all other ambulances to MAINTENANCE so only this 1 is available
    db_session.query(Ambulance).filter(Ambulance.id != amb_id).update({"status": AmbulanceStatusEnum.MAINTENANCE})
    db_session.commit()

    # Pre-create 10 valid Emergency records for the 10 competing worker threads
    worker_emg_ids = [f"emg-race-worker-{i}-{uuid.uuid4().hex[:4]}" for i in range(10)]
    for w_id in worker_emg_ids:
        w_emg = Emergency(
            id=w_id,
            patient_id=f"pat-race-{w_id[-4:]}",
            emergency_type="ACUTE_CARDIO_RESPIRATORY",
            priority=PriorityEnum.P2_EMERGENCY,
            patient_latitude=12.9716,
            patient_longitude=77.5946,
            required_bed_type=BedTypeEnum.ICU,
            selected_hospital_id="hosp-manipal-hal"
        )
        db_session.add(w_emg)
    db_session.commit()

    from tests.conftest import TestingSessionLocal

    results = []
    lock = threading.Lock()

    def dispatch_worker(thread_idx: int):
        thread_db = TestingSessionLocal()
        thread_emg_id = worker_emg_ids[thread_idx]
        try:
            res = AmbulanceDispatchService.dispatch_for_emergency(
                db=thread_db,
                emergency_id=thread_emg_id,
                hospital_id="hosp-manipal-hal"
            )
            with lock:
                results.append((thread_idx, res))
        finally:
            thread_db.close()

    # Launch 10 concurrent threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(dispatch_worker, i) for i in range(10)]
        for f in futures:
            f.result()

    successful_dispatches = [r for r in results if r[1] is not None]
    failed_dispatches = [r for r in results if r[1] is None]

    # Exactly 1 winner, exactly 9 clean rejections
    assert len(successful_dispatches) == 1
    assert len(failed_dispatches) == 9

    # Verify winner acquired our candidate ambulance
    winner_amb = successful_dispatches[0][1]
    assert winner_amb.ambulanceId == amb_id

    # Verify database state in main session
    db_session.expire_all()
    locked_amb = db_session.query(Ambulance).filter(Ambulance.id == amb_id).one()
    assert locked_amb.status == AmbulanceStatusEnum.ASSIGNED
    assert locked_amb.assigned_emergency_id is not None


def test_update_status_rejects_manual_assignment(db_session: Session):
    """
    Verifies that AmbulanceDispatchService.update_status() rejects manual
    AVAILABLE -> ASSIGNED transitions, enforcing that assignment must be
    initiated through hospital-coordinated dispatch.
    """
    amb_id = f"amb-manual-assign-{uuid.uuid4().hex[:6]}"
    test_amb = Ambulance(
        id=amb_id,
        vehicle_number=f"KA-MAN-{uuid.uuid4().hex[:4].upper()}",
        driver_name="Manual Test Driver",
        driver_contact="+91-99999-22222",
        ambulance_type=AmbulanceTypeEnum.ALS,
        equipment_tags="VENTILATOR,OXYGEN",
        status=AmbulanceStatusEnum.AVAILABLE,
        current_latitude=12.9716,
        current_longitude=77.5946,
        current_address="Manual Assignment Standby",
        assigned_emergency_id=None,
        destination_hospital_id=None,
        route_progress=0.0,
        version=1,
    )
    db_session.add(test_amb)
    db_session.commit()

    with pytest.raises(ValueError, match="hospital-coordinated dispatch"):
        AmbulanceDispatchService.update_status(
            db=db_session,
            ambulance_id=amb_id,
            new_status=AmbulanceStatusEnum.ASSIGNED,
        )


def test_update_status_rejects_mission_transition_without_assignment(db_session: Session):
    """
    Verifies that AmbulanceDispatchService.update_status() rejects transitions
    into active mission stages (e.g. EN_ROUTE_HOSPITAL) when the ambulance has no
    assigned emergency or destination hospital.
    """
    amb_id = f"amb-no-assign-{uuid.uuid4().hex[:6]}"
    test_amb = Ambulance(
        id=amb_id,
        vehicle_number=f"KA-NOA-{uuid.uuid4().hex[:4].upper()}",
        driver_name="Unassigned Mission Driver",
        driver_contact="+91-99999-33333",
        ambulance_type=AmbulanceTypeEnum.ALS,
        equipment_tags="VENTILATOR,OXYGEN",
        status=AmbulanceStatusEnum.ASSIGNED,
        current_latitude=12.9716,
        current_longitude=77.5946,
        current_address="Unassigned Location",
        assigned_emergency_id=None,
        destination_hospital_id=None,
        route_progress=0.0,
        version=1,
    )
    db_session.add(test_amb)
    db_session.commit()

    with pytest.raises(ValueError, match="active emergency assignment and destination hospital"):
        AmbulanceDispatchService.update_status(
            db=db_session,
            ambulance_id=amb_id,
            new_status=AmbulanceStatusEnum.EN_ROUTE_HOSPITAL,
        )
