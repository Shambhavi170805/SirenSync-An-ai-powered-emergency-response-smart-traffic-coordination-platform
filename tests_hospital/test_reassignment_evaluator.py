"""
Tests for 40% Policy & Audit Reassignment Evaluator Testbed.

Validates:
1. Scenario C (< 40% route progress): Reassignment approved, reservation released,
   displacing reservation created, reroute event emitted, audit entry committed.
2. Scenario D (>= 40% route progress): Reassignment rejected, inbound reservation retained,
   no reroute event, audit entry committed.
3. Sequential executions (C -> D -> C): Creates distinct, persisted audit ledger records.
4. HTTP API endpoints (/api/v1/reassignment/evaluate and /api/v1/reassignment/audit).
5. Repeatability: Multiple consecutive runs execute cleanly without candidate exhaustion.
"""

import pytest
from backend.services.reassignment_service import BedReassignmentService
from backend.models.enums import PriorityEnum, BedTypeEnum, ReservationStatusEnum
from backend.models.audit import ReassignmentAuditLog
from backend.schemas.reassignment import ReassignmentEvaluationRequest
from backend.shared.contracts import CoordinatesContract, EVENT_BED_REASSIGNMENT_REROUTE


def test_evaluator_scenario_c_approved(db_session):
    """
    Scenario C (< 40% Route Progress):
    Simulated 25% route progress allows priority escalation from P1 over P3.
    Verifies state transitions, reroute event generation, and persistent audit entry.
    """
    req = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-eval-c-001",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId="hosp-manipal-hal",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946, address="HAL Airport Road"),
        simulatedRouteProgress=25.0
    )

    resp = BedReassignmentService.evaluate_and_reassign(db_session, req)

    assert resp.decision == "REASSIGNMENT_APPROVED"
    assert resp.routeProgress == 25.0
    assert resp.thresholdPercent == 40.0
    assert resp.displacedReservationStatus == "RELEASED_FOR_REASSIGNMENT"
    assert resp.rerouteRequired is True
    assert "Scenario C" in (resp.scenarioName or "")

    # Displacing reservation allocated
    assert resp.displacingReservation is not None
    assert resp.displacingReservation.status == ReservationStatusEnum.RESERVED
    assert resp.displacingReservation.bedType == BedTypeEnum.ICU

    # Machine-readable reroute event emitted for ambulance coordination (Nidhi)
    assert resp.rerouteEvent is not None
    assert resp.rerouteEvent.eventType == EVENT_BED_REASSIGNMENT_REROUTE
    assert resp.rerouteEvent.routeProgress == 25.0
    assert resp.rerouteEvent.status == "REROUTE_REQUIRED"
    assert resp.rerouteEvent.previousHospitalId == "hosp-manipal-hal"

    # Audit log persisted in database
    audit = (
        db_session.query(ReassignmentAuditLog)
        .filter(ReassignmentAuditLog.displacing_emergency_id == "emg-eval-c-001")
        .first()
    )
    assert audit is not None
    assert audit.decision == "REASSIGNMENT_APPROVED"
    assert audit.route_progress == 25.0
    assert audit.threshold == 40.0


def test_evaluator_scenario_d_rejected(db_session):
    """
    Scenario D (>= 40% Route Progress):
    Simulated 65% route progress triggers non-disruption protection.
    Inbound reservation is retained, reassignment is rejected, no reroute emitted,
    and audit entry is committed.
    """
    req = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-eval-d-001",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId="hosp-manipal-hal",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946, address="HAL Airport Road"),
        simulatedRouteProgress=65.0
    )

    resp = BedReassignmentService.evaluate_and_reassign(db_session, req)

    assert resp.decision == "REASSIGNMENT_REJECTED"
    assert resp.routeProgress == 65.0
    assert resp.thresholdPercent == 40.0
    assert resp.displacedReservationStatus == "RESERVED"
    assert resp.rerouteRequired is False
    assert resp.rerouteEvent is None
    assert resp.displacingReservation is None
    assert "Scenario D" in (resp.scenarioName or "")

    # Audit log persisted in database
    audit = (
        db_session.query(ReassignmentAuditLog)
        .filter(ReassignmentAuditLog.displacing_emergency_id == "emg-eval-d-001")
        .first()
    )
    assert audit is not None
    assert audit.decision == "REASSIGNMENT_REJECTED"
    assert audit.route_progress == 65.0
    assert audit.threshold == 40.0
    assert "journey stability preserved" in audit.reason.lower() or "threshold" in audit.reason.lower()


def test_evaluator_sequence_c_d_c_generates_distinct_persisted_audits(db_session):
    """
    Sequence C -> D -> C must produce 3 distinct, non-cached persisted audit entries.
    Demonstrates dynamic audit trail updating with each evaluator execution.
    """
    initial_audit_count = db_session.query(ReassignmentAuditLog).count()

    # Run 1: Scenario C (25%)
    req1 = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-seq-c1",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId="hosp-manipal-hal",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946),
        simulatedRouteProgress=25.0
    )
    resp1 = BedReassignmentService.evaluate_and_reassign(db_session, req1)
    assert resp1.decision == "REASSIGNMENT_APPROVED"

    # Run 2: Scenario D (65%)
    req2 = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-seq-d2",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId="hosp-manipal-hal",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946),
        simulatedRouteProgress=65.0
    )
    resp2 = BedReassignmentService.evaluate_and_reassign(db_session, req2)
    assert resp2.decision == "REASSIGNMENT_REJECTED"

    # Run 3: Scenario C (25%)
    req3 = ReassignmentEvaluationRequest(
        displacingEmergencyId="emg-seq-c3",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        targetHospitalId="hosp-manipal-hal",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946),
        simulatedRouteProgress=25.0
    )
    resp3 = BedReassignmentService.evaluate_and_reassign(db_session, req3)
    assert resp3.decision == "REASSIGNMENT_APPROVED"

    # Verify 3 distinct rows were added to the audit database
    final_audit_count = db_session.query(ReassignmentAuditLog).count()
    assert final_audit_count == initial_audit_count + 3

    # Check newest audits in order
    recent_audits = (
        db_session.query(ReassignmentAuditLog)
        .order_by(ReassignmentAuditLog.created_at.desc())
        .limit(3)
        .all()
    )
    assert recent_audits[0].displacing_emergency_id == "emg-seq-c3"
    assert recent_audits[0].decision == "REASSIGNMENT_APPROVED"
    assert recent_audits[1].displacing_emergency_id == "emg-seq-d2"
    assert recent_audits[1].decision == "REASSIGNMENT_REJECTED"
    assert recent_audits[2].displacing_emergency_id == "emg-seq-c1"
    assert recent_audits[2].decision == "REASSIGNMENT_APPROVED"


def test_api_reassignment_evaluate_and_audit(client):
    """
    Test FastAPI endpoints /api/v1/reassignment/evaluate and /api/v1/reassignment/audit
    via TestClient simulating dashboard frontend requests.
    """
    # Test Scenario C via HTTP POST
    post_c = client.post("/api/v1/reassignment/evaluate", json={
        "displacingEmergencyId": "emg-api-c",
        "displacingPriority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "targetHospitalId": "hosp-apollo-bg",
        "patientLocation": {"latitude": 12.8900, "longitude": 77.5980},
        "simulatedRouteProgress": 25.0
    })
    assert post_c.status_code == 200
    data_c = post_c.json()
    assert data_c["decision"] == "REASSIGNMENT_APPROVED"
    assert data_c["routeProgress"] == 25.0
    assert data_c["rerouteRequired"] is True
    assert data_c["rerouteEvent"] is not None
    assert data_c["rerouteEvent"]["eventType"] == EVENT_BED_REASSIGNMENT_REROUTE

    # Test Scenario D via HTTP POST
    post_d = client.post("/api/v1/reassignment/evaluate", json={
        "displacingEmergencyId": "emg-api-d",
        "displacingPriority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "targetHospitalId": "hosp-apollo-bg",
        "patientLocation": {"latitude": 12.8900, "longitude": 77.5980},
        "simulatedRouteProgress": 65.0
    })
    assert post_d.status_code == 200
    data_d = post_d.json()
    assert data_d["decision"] == "REASSIGNMENT_REJECTED"
    assert data_d["routeProgress"] == 65.0
    assert data_d["rerouteRequired"] is False
    assert data_d["rerouteEvent"] is None

    # Test Audit endpoint via HTTP GET
    audit_resp = client.get("/api/v1/reassignment/audit")
    assert audit_resp.status_code == 200
    audits = audit_resp.json()
    assert isinstance(audits, list)
    assert len(audits) >= 2

    # Verify latest audit is Scenario D
    assert audits[0]["displacingEmergencyId"] == "emg-api-d"
    assert audits[0]["decision"] == "REASSIGNMENT_REJECTED"
    assert audits[0]["routeProgress"] == 65.0


def test_evaluator_repeatability_without_exhaustion(db_session):
    """
    Evaluator testbed must be repeatable indefinitely without exhausting candidates.
    Executing Scenario C 5 times in a row must succeed every time.
    """
    for i in range(5):
        req = ReassignmentEvaluationRequest(
            displacingEmergencyId=f"emg-repeat-{i}",
            displacingPriority=PriorityEnum.P1_CRITICAL,
            requiredBedType=BedTypeEnum.ICU,
            targetHospitalId="hosp-fortis-cunningham",
            patientLocation=CoordinatesContract(latitude=12.8950, longitude=77.5980),
            simulatedRouteProgress=25.0
        )
        resp = BedReassignmentService.evaluate_and_reassign(db_session, req)
        assert resp.decision == "REASSIGNMENT_APPROVED"
        assert resp.rerouteRequired is True
