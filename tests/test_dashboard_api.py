import pytest
from backend.models.enums import BedStatusEnum

def test_get_hospital_dashboard_overview(client):
    # Fetch first hospital from directory
    hosp_res = client.get("/api/v1/hospitals")
    assert hosp_res.status_code == 200
    hospitals = hosp_res.json()
    assert len(hospitals) > 0
    hosp_id = hospitals[0]["id"]

    # Request dashboard overview
    dash_res = client.get(f"/api/v1/hospitals/{hosp_id}/dashboard")
    assert dash_res.status_code == 200
    data = dash_res.json()

    assert data["hospital"]["id"] == hosp_id
    assert "capabilities" in data["hospital"]
    assert "bedSummary" in data
    assert "by_category" in data["bedSummary"]
    assert "queue" in data
    assert isinstance(data["queue"], list)
    assert "activeReservationsCount" in data
    assert "totalQueueCount" in data

def test_get_hospital_queue_endpoint(client):
    hosp_res = client.get("/api/v1/hospitals")
    hosp_id = hosp_res.json()[0]["id"]

    q_res = client.get(f"/api/v1/hospitals/{hosp_id}/queue")
    assert q_res.status_code == 200
    items = q_res.json()
    assert isinstance(items, list)

def test_get_hospital_reservations_endpoint(client):
    hosp_res = client.get("/api/v1/hospitals")
    hosp_id = hosp_res.json()[0]["id"]

    res_list = client.get(f"/api/v1/hospitals/{hosp_id}/reservations")
    assert res_list.status_code == 200
    items = res_list.json()
    assert isinstance(items, list)

def test_update_bed_status_flow(client):
    hosp_res = client.get("/api/v1/hospitals")
    hosp_id = hosp_res.json()[0]["id"]

    beds_res = client.get(f"/api/v1/hospitals/{hosp_id}/beds")
    assert beds_res.status_code == 200
    beds = beds_res.json()
    assert len(beds) > 0
    target_bed_id = beds[0]["id"]

    # 1. Update status to OCCUPIED
    patch_res = client.patch(
        f"/api/v1/hospitals/{hosp_id}/beds/{target_bed_id}/status",
        json={"status": "OCCUPIED"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "OCCUPIED"

    # 2. Reset status back to AVAILABLE
    reset_res = client.patch(
        f"/api/v1/hospitals/{hosp_id}/beds/{target_bed_id}/status",
        json={"status": "AVAILABLE"}
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "AVAILABLE"

def test_dashboard_not_found_handling(client):
    r = client.get("/api/v1/hospitals/hosp-non-existent-999/dashboard")
    assert r.status_code == 404

    q = client.get("/api/v1/hospitals/hosp-non-existent-999/queue")
    assert q.status_code == 404

    res = client.get("/api/v1/hospitals/hosp-non-existent-999/reservations")
    assert res.status_code == 404

    patch = client.patch(
        "/api/v1/hospitals/hosp-manipal-hal/beds/bed-non-existent/status",
        json={"status": "OCCUPIED"}
    )
    assert patch.status_code == 404

def test_dashboard_html_served(client):
    res = client.get("/dashboard/")
    assert res.status_code == 200
    assert "SirenSync" in res.text
    assert "Hospital Operations" in res.text

