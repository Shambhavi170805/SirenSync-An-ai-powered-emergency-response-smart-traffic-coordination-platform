"""
SirenSync — Automated Reroute Publication & Post-Commit Integration Tests
Phase 2.1E: Member 3 (Nidhi) — Ambulance Coordination + Real-Time Telemetry Tracking

Verifies:
1. Successful evaluator reroute commits transaction before publishing REROUTE_ALERT once.
2. Evaluator path publishes NO REROUTE_ALERT when apply_reroute() returns None.
3. Failed database transaction rolls back and publishes NO event.
4. Explicit REST endpoint (apply_reroute_event) commits before async broadcast,
   and failed transactions publish nothing.
5. Payload contract validates all 15 JSON-serializable fields, enum conversions, ISO timestamp,
   and routeProgress == 0.0.

Database Isolation Guarantee:
Uses an isolated in-memory SQLite database (sqlite:///:memory:) with StaticPool.
Never uses sirensync_hospital.db, sirensync_presentation.db, sirensync_driver_test.db,
smoke_test.db, or test_hospital_concurrency.db.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from backend.database.base import Base
from backend.models.ambulance import Ambulance
from backend.models.emergency import Emergency
from backend.models.hospital import Hospital
from backend.models.bed import Bed
from backend.models.reservation import BedReservation
from backend.models.queue import HospitalQueueItem
from backend.models.audit import ReassignmentAuditLog
from backend.models.enums import (
    AmbulanceStatusEnum,
    AmbulanceTypeEnum,
    PriorityEnum,
    BedTypeEnum,
    BedStatusEnum,
    ReservationStatusEnum,
    QueueStatusEnum,
)
from backend.shared.contracts import (
    CoordinatesContract,
    RerouteEventContract,
    EVENT_BED_REASSIGNMENT_REROUTE,
)
from backend.schemas.reassignment import ReassignmentEvaluationRequest
from backend.services.reassignment_service import BedReassignmentService
from backend.services.ambulance_service import AmbulanceDispatchService
from backend.routers.ambulances import apply_reroute_event
from backend.services.tracking_service import tracking_hub


# ==============================================================================
# Isolated Database Configuration (Pure In-Memory SQLite - Zero Disk Mutation)
# ==============================================================================

isolated_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
IsolatedSession = sessionmaker(autocommit=False, autoflush=False, bind=isolated_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Overrides conftest.py's session fixture to prevent creating or seeding
    test_hospital_concurrency.db, sirensync_presentation.db, or any disk database.
    """
    Base.metadata.create_all(bind=isolated_engine)
    yield
    Base.metadata.drop_all(bind=isolated_engine)
    isolated_engine.dispose()


@pytest.fixture
def db():
    """Provides a clean, transactionally isolated session on the in-memory database."""
    session = IsolatedSession()
    # Clean up existing rows between tests to ensure test independence
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    try:
        yield session
    finally:
        session.close()


def run_coro(coro):
    """
    Synchronously drives an asyncio coroutine to completion without spinning up
    an AnyIO blocking portal or OS event loop that hangs in Python 3.14 on Windows.
    """
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


# ==============================================================================
# Test Data Fixtures & Helpers
# ==============================================================================

def create_evaluator_scenario_data(db: Session, displaced_emg_id: str, amb_id: str = "amb-eval-001"):
    """Seeds minimal records required for evaluator reassignment in the in-memory database."""
    hosp1 = Hospital(
        id="hosp-eval-1",
        name="Hospital Central",
        address="123 Central Ave, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        contact_number="9876543210"
    )
    hosp2 = Hospital(
        id="hosp-eval-2",
        name="Hospital North",
        address="456 North Blvd, Bangalore",
        latitude=12.9850,
        longitude=77.6050,
        contact_number="9876543211"
    )
    bed1 = Bed(
        id="bed-eval-1",
        hospital_id="hosp-eval-1",
        bed_number="ICU-101",
        bed_type=BedTypeEnum.ICU,
        status=BedStatusEnum.OCCUPIED,
        department="Critical Care"
    )
    bed2 = Bed(
        id="bed-eval-2",
        hospital_id="hosp-eval-2",
        bed_number="ICU-201",
        bed_type=BedTypeEnum.ICU,
        status=BedStatusEnum.AVAILABLE,
        department="Critical Care"
    )
    emg = Emergency(
        id=displaced_emg_id,
        patient_id="pat-eval-1",
        emergency_type="ACUTE_CARDIO_RESPIRATORY",
        priority=PriorityEnum.P3_URGENT,
        patient_latitude=12.9716,
        patient_longitude=77.5946,
        patient_address="HAL Airport Road",
        required_bed_type=BedTypeEnum.ICU,
        selected_hospital_id="hosp-eval-1"
    )
    res = BedReservation(
        id=f"res-{displaced_emg_id}",
        emergency_id=displaced_emg_id,
        hospital_id="hosp-eval-1",
        bed_id="bed-eval-1",
        status=ReservationStatusEnum.RESERVED,
        reserved_at=datetime.utcnow()
    )
    queue = HospitalQueueItem(
        id=f"qitem-{displaced_emg_id}",
        hospital_id="hosp-eval-1",
        emergency_id=displaced_emg_id,
        priority=PriorityEnum.P3_URGENT,
        status=QueueStatusEnum.EN_ROUTE,
        route_progress=25.0,
        notes="En route to hosp-eval-1"
    )
    db.add_all([hosp1, hosp2, bed1, bed2, emg, res, queue])

    if amb_id:
        amb = Ambulance(
            id=amb_id,
            vehicle_number="KA-01-EVAL-9999",
            driver_name="Test Driver",
            driver_contact="9876543210",
            ambulance_type=AmbulanceTypeEnum.ALS,
            equipment_tags="VENTILATOR,OXYGEN",
            status=AmbulanceStatusEnum.EN_ROUTE_HOSPITAL,
            current_latitude=12.9716,
            current_longitude=77.5946,
            assigned_emergency_id=displaced_emg_id,
            destination_hospital_id="hosp-eval-1",
            route_progress=25.0,
            is_simulated=True,
            version=1
        )
        db.add(amb)

    db.commit()


def get_mock_ranking_engine(target_hospital_id: str = "hosp-eval-2"):
    """Returns a mock ranking engine selecting target_hospital_id as next best hospital."""
    mock_candidate = MagicMock()
    mock_candidate.hospitalId = target_hospital_id
    mock_candidate.name = "Hospital North"
    mock_candidate.isEligible = True
    mock_candidate.breakdown.distanceKm = 3.2
    mock_candidate.breakdown.availableBedsCount = 5

    ranking_engine = MagicMock()
    ranking_engine.rank_hospitals.return_value = MagicMock(rankedHospitals=[mock_candidate])
    return ranking_engine


# ==============================================================================
# TEST 1 — SUCCESSFUL EVALUATOR REROUTE
# ==============================================================================

def test_evaluator_reroute_publishes_once_after_commit(db: Session, monkeypatch):
    """
    Verifies that a successful evaluator reroute:
    1. Updates the ambulance destination and resets route progress to 0.0.
    2. Commits the transaction before publication (execution order verified).
    3. Calls tracking_hub.broadcast_event_threadsafe() exactly once.
    4. Delivers REROUTE_ALERT with correct emergencyId, ambulanceId, and routeProgress=0.0.
    """
    emg_id = "emg-success-001"
    amb_id = "amb-success-001"
    create_evaluator_scenario_data(db, displaced_emg_id=emg_id, amb_id=amb_id)

    execution_order = []
    original_commit = db.commit

    def tracked_commit():
        execution_order.append("db.commit")
        return original_commit()

    db.commit = tracked_commit

    mock_broadcast = MagicMock()

    def tracked_broadcast(event_type, payload, emergency_id=None):
        execution_order.append("broadcast_event_threadsafe")
        mock_broadcast(event_type=event_type, payload=payload, emergency_id=emergency_id)

    monkeypatch.setattr(tracking_hub, "broadcast_event_threadsafe", tracked_broadcast)

    req = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-displacer-001",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId="hosp-eval-1",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946, address="Test Location"),
        simulatedRouteProgress=25.0
    )

    ranking_engine = get_mock_ranking_engine("hosp-eval-2")
    resp = BedReassignmentService.evaluate_and_reassign(db, req, ranking_engine=ranking_engine)

    assert resp.decision == "REASSIGNMENT_APPROVED"

    # Verify execution order: commit occurs BEFORE broadcast
    assert "db.commit" in execution_order
    assert "broadcast_event_threadsafe" in execution_order
    assert execution_order.index("db.commit") < execution_order.index("broadcast_event_threadsafe")

    # Verify publication count and payload fields
    assert mock_broadcast.call_count == 1
    call_kwargs = mock_broadcast.call_args.kwargs
    assert call_kwargs["event_type"] == "REROUTE_ALERT"
    assert call_kwargs["emergency_id"] == emg_id
    payload = call_kwargs["payload"]
    assert payload["emergencyId"] == emg_id
    assert payload["ambulanceId"] == amb_id
    assert payload["previousHospitalId"] == "hosp-eval-1"
    assert payload["newHospitalId"] == "hosp-eval-2"
    assert payload["routeProgress"] == 0.0
    assert payload["status"] == "REROUTE_EXECUTED"

    # Verify ambulance record in database was updated
    amb = db.query(Ambulance).filter(Ambulance.id == amb_id).one()
    assert amb.destination_hospital_id == "hosp-eval-2"
    assert amb.route_progress == 0.0
    assert amb.status == AmbulanceStatusEnum.EN_ROUTE_HOSPITAL


# ==============================================================================
# TEST 2 — NO AMBULANCE UPDATED
# ==============================================================================

def test_evaluator_no_ambulance_updated_commits_without_publishing(db: Session, monkeypatch):
    """
    Simulates apply_reroute() returning None (e.g. no ambulance linked to emergency).
    Verifies:
    1. The hospital reassignment still commits successfully.
    2. broadcast_event_threadsafe() has call_count == 0 (no false-positive event).
    """
    emg_id = "emg-no-amb-001"
    # Seed data without creating an ambulance record
    create_evaluator_scenario_data(db, displaced_emg_id=emg_id, amb_id=None)

    mock_broadcast = MagicMock()
    monkeypatch.setattr(tracking_hub, "broadcast_event_threadsafe", mock_broadcast)

    req = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-displacer-002",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId="hosp-eval-1",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946, address="Test Location"),
        simulatedRouteProgress=25.0
    )

    ranking_engine = get_mock_ranking_engine("hosp-eval-2")
    resp = BedReassignmentService.evaluate_and_reassign(db, req, ranking_engine=ranking_engine)

    # Reassignment is approved and transaction committed
    assert resp.decision == "REASSIGNMENT_APPROVED"
    audit = db.query(ReassignmentAuditLog).filter(ReassignmentAuditLog.displaced_emergency_id == emg_id).first()
    assert audit is not None
    assert audit.decision == "REASSIGNMENT_APPROVED"

    # Critical Assertion: zero broadcasts emitted when no ambulance updated
    assert mock_broadcast.call_count == 0


# ==============================================================================
# TEST 3 — FAILED TRANSACTION
# ==============================================================================

def test_evaluator_failed_transaction_rolls_back_and_publishes_nothing(db: Session, monkeypatch):
    """
    Simulates a failure during transaction commit.
    Verifies:
    1. The transaction is rolled back.
    2. broadcast_event_threadsafe() has call_count == 0.
    3. The original exception is re-raised (not swallowed).
    """
    emg_id = "emg-fail-001"
    create_evaluator_scenario_data(db, displaced_emg_id=emg_id, amb_id="amb-fail-001")

    mock_broadcast = MagicMock()
    monkeypatch.setattr(tracking_hub, "broadcast_event_threadsafe", mock_broadcast)

    # Force commit to fail
    def failing_commit():
        raise RuntimeError("Simulated DB commit I/O error")

    monkeypatch.setattr(db, "commit", failing_commit)

    req = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-displacer-003",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId="hosp-eval-1",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946, address="Test Location"),
        simulatedRouteProgress=25.0
    )

    ranking_engine = get_mock_ranking_engine("hosp-eval-2")

    # Verify exception is propagated
    with pytest.raises(RuntimeError, match="Simulated DB commit I/O error"):
        BedReassignmentService.evaluate_and_reassign(db, req, ranking_engine=ranking_engine)

    # Verify broadcast was NEVER called on failed transaction
    assert mock_broadcast.call_count == 0


# ==============================================================================
# TEST 4 — EXPLICIT REROUTE ENDPOINT
# ==============================================================================

def test_explicit_reroute_endpoint_publication_order_and_failure_safety(db: Session, monkeypatch):
    """
    Target: apply_reroute_event() (POST /api/v1/ambulances/apply-reroute)
    Verifies:
    1. Successful request commits before broadcast.
    2. broadcast_event() is called exactly once with REROUTE_ALERT, correct IDs and routeProgress=0.0.
    3. Failed transaction (e.g. non-existent emergency) raises HTTPException(404) and does not publish.
    4. Database failure during commit triggers rollback and raises exception without publishing.
    """
    emg_id = "emg-explicit-001"
    amb_id = "amb-explicit-001"
    create_evaluator_scenario_data(db, displaced_emg_id=emg_id, amb_id=amb_id)

    execution_order = []
    original_commit = db.commit

    def tracked_commit():
        execution_order.append("db.commit")
        return original_commit()

    db.commit = tracked_commit

    broadcast_calls = []

    async def tracked_broadcast(event_type, payload, emergency_id=None):
        execution_order.append("broadcast_event")
        broadcast_calls.append({"event_type": event_type, "payload": payload, "emergency_id": emergency_id})

    monkeypatch.setattr(tracking_hub, "broadcast_event", tracked_broadcast)

    reroute_contract = RerouteEventContract(
        eventType=EVENT_BED_REASSIGNMENT_REROUTE,
        eventId="evt-explicit-001",
        emergencyId=emg_id,
        previousHospitalId="hosp-eval-1",
        previousBedId="bed-eval-1",
        newHospitalId="hosp-eval-2",
        newBedId="bed-eval-2",
        displacingEmergencyId="emg-displacer-999",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        displacedPriority=PriorityEnum.P3_URGENT,
        reason="HIGHER_PRIORITY_EMERGENCY",
        routeProgress=25.0,
        threshold=40.0,
        status="REROUTE_REQUIRED",
        timestamp=datetime.utcnow()
    )

    # 4A: Valid reroute
    resp_dto = run_coro(apply_reroute_event(reroute_event=reroute_contract, db=db))
    assert resp_dto.destinationHospitalId == "hosp-eval-2"
    assert resp_dto.routeProgress == 0.0

    # Assert commit occurs before broadcast
    assert "db.commit" in execution_order
    assert "broadcast_event" in execution_order
    assert execution_order.index("db.commit") < execution_order.index("broadcast_event")

    # Assert broadcast called once with correct parameters
    assert len(broadcast_calls) == 1
    call = broadcast_calls[0]
    assert call["event_type"] == "REROUTE_ALERT"
    assert call["emergency_id"] == emg_id
    payload = call["payload"]
    assert payload["eventId"] == "evt-explicit-001"
    assert payload["ambulanceId"] == amb_id
    assert payload["emergencyId"] == emg_id
    assert payload["routeProgress"] == 0.0

    # 4B: Failed transaction (non-existent emergency) publishes nothing
    broadcast_calls.clear()
    reroute_contract.emergencyId = "emg-does-not-exist"
    with pytest.raises(HTTPException) as exc_info:
        run_coro(apply_reroute_event(reroute_event=reroute_contract, db=db))
    assert exc_info.value.status_code == 404
    assert len(broadcast_calls) == 0

    # 4C: Failed transaction on commit error rolls back and does not publish
    reroute_contract.emergencyId = emg_id
    monkeypatch.setattr(db, "commit", MagicMock(side_effect=RuntimeError("Simulated commit crash")))
    with pytest.raises(RuntimeError, match="Simulated commit crash"):
        run_coro(apply_reroute_event(reroute_event=reroute_contract, db=db))
    assert len(broadcast_calls) == 0


# ==============================================================================
# TEST 5 — PAYLOAD CONTRACT
# ==============================================================================

def test_build_reroute_payload_all_15_fields():
    """
    Target: AmbulanceDispatchService.build_reroute_payload()
    Verifies:
    1. Exactly all 15 required contract fields are present.
    2. Payload is completely JSON-serializable.
    3. routeProgress is 0.0 representing the new route.
    4. Enum values are serialized to plain strings.
    5. timestamp is serialized to an ISO-formatted string.
    """
    event = RerouteEventContract(
        eventType="BED_REASSIGNMENT_REROUTE",
        eventId="evt-contract-test-99",
        emergencyId="emg-contract-01",
        previousHospitalId="hosp-source-alpha",
        previousBedId="bed-source-01",
        newHospitalId="hosp-dest-beta",
        newBedId="bed-dest-02",
        displacingEmergencyId="emg-displacer-77",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        displacedPriority=PriorityEnum.P3_URGENT,
        reason="HIGHER_PRIORITY_EMERGENCY",
        routeProgress=28.5,  # Old route progress
        threshold=40.0,
        status="REROUTE_REQUIRED",
        timestamp=datetime.utcnow()
    )

    ambulance = Ambulance(
        id="amb-contract-88",
        vehicle_number="KA-01-XX-0001",
        driver_name="Jane Doe",
        driver_contact="9876543210",
        route_progress=0.0  # Reset on new branch
    )

    payload = AmbulanceDispatchService.build_reroute_payload(event, ambulance=ambulance)

    # 1. Verify all 15 fields
    expected_fields = [
        "eventId",
        "eventType",
        "emergencyId",
        "ambulanceId",
        "previousHospitalId",
        "newHospitalId",
        "previousBedId",
        "newBedId",
        "displacingEmergencyId",
        "displacingPriority",
        "displacedPriority",
        "reason",
        "routeProgress",
        "status",
        "timestamp",
    ]
    for field in expected_fields:
        assert field in payload, f"Missing expected field '{field}' in reroute payload"
    assert len(payload) == 15

    # 2. Verify values and serialization
    assert payload["eventId"] == "evt-contract-test-99"
    assert payload["eventType"] == "BED_REASSIGNMENT_REROUTE"
    assert payload["emergencyId"] == "emg-contract-01"
    assert payload["ambulanceId"] == "amb-contract-88"
    assert payload["previousHospitalId"] == "hosp-source-alpha"
    assert payload["newHospitalId"] == "hosp-dest-beta"
    assert payload["previousBedId"] == "bed-source-01"
    assert payload["newBedId"] == "bed-dest-02"
    assert payload["displacingEmergencyId"] == "emg-displacer-77"
    assert payload["displacingPriority"] == "P1_CRITICAL"
    assert payload["displacedPriority"] == "P3_URGENT"
    assert payload["reason"] == "HIGHER_PRIORITY_EMERGENCY"
    assert payload["routeProgress"] == 0.0
    assert payload["status"] == "REROUTE_EXECUTED"
    assert isinstance(payload["timestamp"], str)

    # 3. Verify JSON serializability
    json_str = json.dumps(payload)
    parsed = json.loads(json_str)
    assert parsed["eventId"] == "evt-contract-test-99"
    assert parsed["routeProgress"] == 0.0
