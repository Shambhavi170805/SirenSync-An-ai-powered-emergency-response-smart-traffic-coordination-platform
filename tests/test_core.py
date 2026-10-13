"""
Core tests: verifies signal state transitions, 200m corridor trigger, /health endpoint,
and ANPR plate normalisation / fuzzy matching.
"""

import pytest
from fastapi.testclient import TestClient
from ai_traffic.main import app
from ai_traffic.route import calculate_distance_meters, set_active_route, update_ambulance_location
from ai_traffic.signals import (
    get_junction_state,
    init_signals,
    set_state,
    trigger_green,
    trigger_hold,
)
from ai_traffic.plates import normalise_plate, fuzzy_match, match_plate


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

    # Set a route active for the ambulance so update_ambulance_location does not return early
    set_active_route({"ambulance_id": "AMB-TEST-200M"})

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


# Test 4: Exact plate match in registry
def test_anpr_exact_match():
    registry = [{"plate": "KA01AB1234", "ambulance_id": "AMB001", "active": True}]
    norm = normalise_plate("KA01AB1234")
    result = match_plate(norm, registry)
    assert result is not None
    assert result["ambulance_id"] == "AMB001"


# Test 5: OCR confusion fix — O read as 0 in digit position
def test_anpr_ocr_o_confusion():
    registry = [{"plate": "KA01AB1234", "ambulance_id": "AMB001", "active": True}]
    # EasyOCR sometimes reads '0' as 'O'; normalise_plate or fuzzy_match should still find it
    raw_from_ocr = "KAO1AB1234"
    norm = normalise_plate(raw_from_ocr)
    result = match_plate(norm, registry)
    assert result is not None


# Test 6: Wrong plate does not match
def test_anpr_wrong_plate():
    registry = [{"plate": "KA01AB1234", "ambulance_id": "AMB001", "active": True}]
    norm = normalise_plate("MH12ZZ9999")
    result = match_plate(norm, registry)
    assert result is None


# Test 7: Inactive ambulance is not matched
def test_anpr_inactive_ambulance():
    registry = [{"plate": "MH12EF9012", "ambulance_id": "AMB003", "active": False}]
    norm = normalise_plate("MH12EF9012")
    result = match_plate(norm, registry)
    assert result is None


# Test 8: Fuzzy match tolerates exactly 1 character difference
def test_anpr_fuzzy_one_char():
    assert fuzzy_match("KA01AB1234", "KA01AB1235") is True   # last digit differs
    assert fuzzy_match("KA01AB1234", "KA01AB1299") is False  # two digits differ
