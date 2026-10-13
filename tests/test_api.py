"""
FastAPI Integration Tests using TestClient.
Tests endpoints: /health, /junctions, /events, /route, /api/config, and demo dispatch.
"""

import pytest
from fastapi.testclient import TestClient

from ai_traffic.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_get_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "SirenSync Green Corridor"
    assert "controller" in data


def test_get_junctions(client):
    response = client.get("/junctions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check configured junction presence
    j_ids = [j["junction_id"] for j in data]
    assert "J-1" in j_ids


def test_get_client_config(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "junctions" in data
    assert "google_maps_api_key" in data


def test_post_route(client):
    route_payload = {
        "ambulance_id": "AMB-TEST-77",
        "route_points": [
            {"lat": 12.9716, "lng": 77.5946},
            {"lat": 12.9758, "lng": 77.6012}
        ],
        "junctions": ["J-1", "J-2"],
        "progress_percent": 10.0,
        "emergency_severity": "CRITICAL"
    }

    # Ingest Route
    res = client.post("/route", json=route_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"
    assert res.json()["ambulance_id"] == "AMB-TEST-77"


def test_demo_dispatch_updates_signal(client):
    res = client.post("/demo/dispatch")
    assert res.status_code == 200
    assert res.json()["status"] == "dispatched"

    # Verify reflected in /junctions
    j_res = client.get("/junctions")
    j1 = next(j for j in j_res.json() if j["junction_id"] == "J-1")
    assert j1["state"] == "GREEN"


def test_get_events(client):
    res = client.get("/events")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
