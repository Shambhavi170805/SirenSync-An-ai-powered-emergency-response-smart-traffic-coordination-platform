"""
FastAPI Integration Tests using TestClient.
Tests endpoints: /health, /junctions, /events, /route, /route/progress, /api/config.
"""

import pytest
from fastapi.testclient import TestClient

from ai_traffic.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_get_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "controller_info" in data
    assert "cameras" in data


def test_get_junctions(client):
    response = client.get("/junctions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check J-101 presence
    j_ids = [j["junction_id"] for j in data]
    assert "J-101" in j_ids


def test_get_client_config(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "junctions" in data
    assert "cameras" in data
    assert "signal_controller_type" in data


def test_post_route_and_progress(client):
    route_payload = {
        "ambulance_id": "AMB-TEST-77",
        "route_points": [
            {"lat": 12.9716, "lng": 77.5946},
            {"lat": 12.9758, "lng": 77.6012}
        ],
        "junctions": ["J-101", "J-102"],
        "progress_percent": 10.0,
        "emergency_severity": "CRITICAL"
    }

    # Ingest Route
    res = client.post("/route", json=route_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "INGESTED"
    assert res.json()["ambulance_id"] == "AMB-TEST-77"

    # Update Progress
    prog_res = client.post("/route/progress", json={
        "ambulance_id": "AMB-TEST-77",
        "progress_percent": 55.0,
        "current_lat": 12.9730,
        "current_lng": 77.5970
    })
    assert prog_res.status_code == 200
    assert prog_res.json()["progress_percent"] == 55.0


def test_manual_signal_override(client):
    res = client.post("/signals/manual_override?junction_id=J-101&state=GREEN")
    assert res.status_code == 200
    assert res.json()["state"] == "GREEN"

    # Verify reflected in /junctions
    j_res = client.get("/junctions")
    j101 = next(j for j in j_res.json() if j["junction_id"] == "J-101")
    assert j101["state"] == "GREEN"


def test_get_events(client):
    res = client.get("/events?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
