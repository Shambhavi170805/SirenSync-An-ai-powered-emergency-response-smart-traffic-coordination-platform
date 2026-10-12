"""
Core tests: verifies signal state transitions, 200m corridor trigger, and /health endpoint.
"""

from fastapi.testclient import TestClient
from ai_traffic.main import app
from ai_traffic.route import calculate_distance_meters, update_ambulance_location
from ai_traffic.signals import (
    get_junction_state,
    init_signals,
    set_state,
    trigger_green,
    trigger_hold,
)


# Test 1: Signal state machine transitions (RED -> GREEN -> HOLD -> RED)
def test_signal_transitions():
    junctions = [{"id": "J-TEST", "name": "Test Junction"}]
    init_signals(junctions, controller_type="simulated")

    # Initial state is RED
    assert get_junction_state("J-TEST")["state"] == "RED"

    # Turn GREEN
    trigger_green("J-TEST", "AMB-1", reason="TEST_APPROACH")
    assert get_junction_state("J-TEST")["state"] == "GREEN"

    # Turn HOLD
    trigger_hold("J-TEST", "AMB-1")
    assert get_junction_state("J-TEST")["state"] == "HOLD"

    # Back to RED
    set_state("J-TEST", "RED", reason="PASSED")
    assert get_junction_state("J-TEST")["state"] == "RED"


# Test 2: Verify 200 meter corridor trigger logic
def test_200m_trigger():
    junctions = [{"id": "J-1", "lat": 12.9716, "lng": 77.5946}]
    init_signals(junctions)

    # Coords ~150 meters away
    amb_lat, amb_lng = 12.9705, 77.5940
    dist = calculate_distance_meters(amb_lat, amb_lng, 12.9716, 77.5946)
    assert dist < 200.0  # Verify distance is within 200m

    # Update location
    update_ambulance_location(amb_lat, amb_lng, 25.0, junctions, trigger_distance_m=200.0)

    # Signal should now be GREEN
    assert get_junction_state("J-1")["state"] == "GREEN"


# Test 3: /health endpoint returns ok
def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
