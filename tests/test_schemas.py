"""
Unit Tests for Pydantic Event and API Schemas.
Verifies fixed contracts consumed by Patient Intake, Hospital Ranking, and Ambulance Coordination.
"""

import pytest
from pydantic import ValidationError

from ai_traffic.api.schemas import (
    AmbulanceDetectedEvent,
    ConflictDetectedEvent,
    HealthResponse,
    RouteInputRequest,
    RoutePoint,
    RouteUpdatedEvent,
    SignalChangedEvent,
)


def test_ambulance_detected_schema_valid():
    event = AmbulanceDetectedEvent(
        camera_id="CAM-J1-NORTH",
        junction_id="J-101",
        confidence=0.89,
        bounding_box=[120, 80, 260, 240],
        heuristic_used=True,
        consecutive_frames=4
    )
    assert event.event_type == "AMBULANCE_DETECTED"
    assert event.camera_id == "CAM-J1-NORTH"
    assert event.confidence == 0.89
    assert event.bounding_box == [120, 80, 260, 240]
    assert event.timestamp is not None


def test_ambulance_detected_schema_invalid_confidence():
    with pytest.raises(ValidationError):
        AmbulanceDetectedEvent(
            camera_id="CAM-1",
            junction_id="J-1",
            confidence=1.5  # must be <= 1.0
        )


def test_signal_changed_schema():
    event = SignalChangedEvent(
        junction_id="J-101",
        previous_state="RED",
        state="GREEN",
        reason="ROUTE_PROXIMITY_PREEMPTION",
        ambulance_id="AMB-01"
    )
    assert event.event_type == "SIGNAL_CHANGED"
    assert event.state == "GREEN"
    assert event.previous_state == "RED"
    assert event.ambulance_id == "AMB-01"


def test_conflict_detected_schema():
    event = ConflictDetectedEvent(
        junction_id="J-102",
        ambulance_ids=["AMB-01", "AMB-02"],
        prioritized_ambulance="AMB-01",
        reason="Priority override"
    )
    assert event.event_type == "CONFLICT_DETECTED"
    assert len(event.ambulance_ids) == 2
    assert event.prioritized_ambulance == "AMB-01"


def test_route_input_request_schema():
    req = RouteInputRequest(
        ambulance_id="AMB-100",
        route_points=[
            RoutePoint(lat=12.9716, lng=77.5946, speed_kmh=45.0),
            RoutePoint(lat=12.9758, lng=77.6012, speed_kmh=40.0)
        ],
        junctions=["J-101", "J-102"],
        progress_percent=25.0,
        emergency_severity="CRITICAL"
    )
    assert req.ambulance_id == "AMB-100"
    assert len(req.route_points) == 2
    assert req.progress_percent == 25.0
