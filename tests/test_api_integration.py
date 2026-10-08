import pytest

def test_system_root_and_health(client):
    r_root = client.get("/")
    assert r_root.status_code == 200
    data = r_root.json()
    assert data["subsystem"] == "Hospital Intelligence + Bed Management"
    assert data["owner"] == "Samriddhi"
    assert data["status"] == "OPERATIONAL"

    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "HEALTHY"

def test_hospitals_directory_endpoints(client):
    r = client.get("/api/v1/hospitals")
    assert r.status_code == 200
    hospitals = r.json()
    assert len(hospitals) >= 5

    # Test single hospital details
    hosp_id = hospitals[0]["id"]
    r_single = client.get(f"/api/v1/hospitals/{hosp_id}")
    assert r_single.status_code == 200
    hosp_data = r_single.json()
    assert hosp_data["id"] == hosp_id
    assert "capabilities" in hosp_data
    assert "total_beds" in hosp_data
    assert hosp_data["total_beds"] > 0

def test_bed_inventory_and_summary_endpoints(client):
    r_hosp = client.get("/api/v1/hospitals")
    hosp_id = r_hosp.json()[0]["id"]

    # Beds list
    r_beds = client.get(f"/api/v1/hospitals/{hosp_id}/beds")
    assert r_beds.status_code == 200
    beds = r_beds.json()
    assert len(beds) > 0
    assert "bed_type" in beds[0]
    assert "status" in beds[0]

    # Bed summary
    r_sum = client.get(f"/api/v1/hospitals/{hosp_id}/beds/summary")
    assert r_sum.status_code == 200
    summary = r_sum.json()
    assert summary["hospital_id"] == hosp_id
    assert "by_category" in summary
    assert "ICU" in summary["by_category"]

def test_ranking_and_selection_e2e_flow(client):
    # 1. Rank hospitals for emergency
    emergency_id = "emg-e2e-001"
    rank_payload = {
        "emergencyId": emergency_id,
        "patientLocation": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "MG Road Metro Station"
        },
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
    }
    r_rank = client.post("/api/v1/hospitals/rank", json=rank_payload)
    assert r_rank.status_code == 200
    rank_data = r_rank.json()
    assert rank_data["emergencyId"] == emergency_id
    assert len(rank_data["rankedHospitals"]) > 0

    top_hospital = rank_data["rankedHospitals"][0]
    top_hospital_id = top_hospital["hospitalId"]
    assert top_hospital["isEligible"] is True

    # 2. Select the top ranked hospital (Simulating Shambhavi UI patient choice)
    select_payload = {
        "selectedHospitalId": top_hospital_id,
        "requiredBedType": "ICU"
    }
    r_select = client.post(f"/api/v1/emergencies/{emergency_id}/select-hospital", json=select_payload)
    assert r_select.status_code == 201
    select_data = r_select.json()

    assert select_data["status"] == "SUCCESS"
    assert select_data["emergencyId"] == emergency_id
    assert select_data["hospitalId"] == top_hospital_id
    assert select_data["reservation"]["status"] == "RESERVED"
    assert select_data["coordinatingHospital"]["dispatchStatus"] == "AMBULANCE_COORDINATION_INITIATED"

    # 3. Retrieve the created reservation
    reservation_id = select_data["reservation"]["reservationId"]
    r_res = client.get(f"/api/v1/reservations/{reservation_id}")
    assert r_res.status_code == 200
    res_data = r_res.json()
    assert res_data["reservationId"] == reservation_id
    assert res_data["status"] == "RESERVED"

def test_reassignment_audit_endpoint(client):
    r = client.get("/api/v1/reassignment/audit")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
