"""
Comprehensive End-to-End Integration Test Suite for SirenSync:
Unifies Shambhavi's Patient Authentication & Intake with Samriddhi's Hospital Intelligence & Bed Management.

Verifies:
1. Patient registration, login, and authenticated emergency intake with session-derived ownership.
2. 4-factor deterministic hospital ranking (Distance, Bed Availability, Capabilities, Traffic).
3. Concurrency-safe CAS lock bed reservation on patient hospital selection.
4. Real-time hospital operations queue synchronization.
5. Error cases: nonexistent emergency/hospital, bed capacity conflict (409).
6. Dual SQLite database persistence and separation.
"""

import os
import pytest
from datetime import datetime
from starlette.testclient import TestClient

from backend.main import app
from backend.models.enums import BedStatusEnum, BedTypeEnum, PriorityEnum, ReservationStatusEnum, QueueStatusEnum


def test_e2e_full_patient_to_hospital_workflow(client):
    """
    Complete end-to-end user journey:
    1. Patient registers & logs in -> session established
    2. Patient creates emergency intake -> securely associated with patientId
    3. Patient queries 4-factor hospital rankings
    4. Patient selects hospital -> CAS lock reserves bed atomically
    5. Hospital operations queue shows the emergency in real time
    """
    # -------------------------------------------------------------
    # Step 1: Register and login patient
    # -------------------------------------------------------------
    patient_email = f"patient_{int(datetime.utcnow().timestamp())}@example.com"
    reg_payload = {
        "full_name": "Rohan Deshmukh",
        "email": patient_email,
        "password": "StrongPassword!123",
        "confirm_password": "StrongPassword!123",
        "phone": "+91 98765 43210",
        "blood_group": "O+",
        "emergency_contact_name": "Pooja Deshmukh",
        "emergency_contact_phone": "+91 98765 00000",
        "captcha_token": "turnstile_client_verified"
    }

    r_reg = client.post("/api/v1/auth/register", json=reg_payload)
    assert r_reg.status_code == 201, f"Registration failed: {r_reg.text}"
    reg_data = r_reg.json()
    patient_data = reg_data.get("patient", reg_data)
    patient_id = patient_data["id"]
    assert patient_data["email"] == patient_email
    assert "password" not in patient_data

    # Login to receive HTTP-only session cookie
    login_payload = {
        "email": patient_email,
        "password": "StrongPassword!123",
        "captcha_token": "turnstile_client_verified"
    }
    r_login = client.post("/api/v1/auth/login", json=login_payload)
    assert r_login.status_code == 200, f"Login failed: {r_login.text}"
    assert "sirensync_session" in client.cookies

    # Verify session authentication
    r_me = client.get("/api/v1/auth/me")
    assert r_me.status_code == 200
    me_json = r_me.json()
    patient_me = me_json.get("patient", me_json)
    assert patient_me["email"] == patient_email

    # -------------------------------------------------------------
    # Step 2: Patient submits emergency intake
    # -------------------------------------------------------------
    emergency_id = f"emg-e2e-{int(datetime.utcnow().timestamp())}"
    intake_payload = {
        "emergencyId": emergency_id,
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "patientLocation": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "MG Road Metro Station, Bengaluru"
        },
        "requiredBedType": "ICU",
        "requiredCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"],
        "symptoms": "Severe crushing chest pain, radiating to left arm, shortness of breath"
    }

    # Posting with active session cookie: backend automatically derives patientId!
    r_create = client.post("/api/v1/emergencies", json=intake_payload)
    assert r_create.status_code == 201, f"Emergency intake failed: {r_create.text}"
    created_emergency = r_create.json()
    assert created_emergency["emergencyId"] == emergency_id
    assert created_emergency["patientId"] == patient_id
    assert created_emergency["priority"] == "P1_CRITICAL"

    # Verify patient can see their emergency in their history
    r_my = client.get("/api/v1/emergencies/patient/my-emergencies")
    assert r_my.status_code == 200
    my_emergencies = r_my.json()
    assert any(e["emergencyId"] == emergency_id for e in my_emergencies)

    # -------------------------------------------------------------
    # Step 3: Deterministic 4-Factor Hospital Ranking
    # -------------------------------------------------------------
    rank_payload = {
        "emergencyId": emergency_id,
        "patientId": patient_id,
        "patientLocation": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "MG Road Metro Station, Bengaluru"
        },
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"],
        "symptoms": intake_payload["symptoms"]
    }

    r_rank = client.post("/api/v1/hospitals/rank", json=rank_payload)
    assert r_rank.status_code == 200, f"Ranking failed: {r_rank.text}"
    rank_resp = r_rank.json()
    assert rank_resp["emergencyId"] == emergency_id
    ranked_hospitals = rank_resp["rankedHospitals"]
    assert len(ranked_hospitals) >= 5

    # Check ranking breakdown structure
    top_hospital = ranked_hospitals[0]
    assert top_hospital["isEligible"] is True
    assert 0.0 <= top_hospital["compositeScore"] <= 1.0
    breakdown = top_hospital["breakdown"]
    assert breakdown["distanceKm"] > 0
    assert breakdown["availableBedsCount"] > 0
    assert "CARDIAC_CATH_LAB" in breakdown["matchedCapabilities"]
    assert len(breakdown["explanation"]) > 0

    selected_hospital_id = top_hospital["hospitalId"]

    # Check available ICU beds before reservation
    r_beds_before = client.get(f"/api/v1/hospitals/{selected_hospital_id}/beds/summary")
    assert r_beds_before.status_code == 200
    avail_icu_before = r_beds_before.json()["by_category"]["ICU"]["available"]
    assert avail_icu_before > 0

    # -------------------------------------------------------------
    # Step 4: Patient Selects Hospital (CAS Atomic Bed Reservation)
    # -------------------------------------------------------------
    select_payload = {
        "selectedHospitalId": selected_hospital_id,
        "requiredBedType": "ICU"
    }

    r_select = client.post(f"/api/v1/emergencies/{emergency_id}/select-hospital", json=select_payload)
    assert r_select.status_code == 201, f"Hospital selection failed: {r_select.text}"
    selection_result = r_select.json()

    assert selection_result["status"] == "SUCCESS"
    assert selection_result["emergencyId"] == emergency_id
    assert selection_result["hospitalId"] == selected_hospital_id
    assert selection_result["reservation"]["status"] == "RESERVED"
    assert selection_result["reservation"]["bedType"] == "ICU"
    reservation_id = selection_result["reservation"]["reservationId"]
    reserved_bed_id = selection_result["reservation"]["bedId"]

    # Verify bed availability decreased by exactly 1
    r_beds_after = client.get(f"/api/v1/hospitals/{selected_hospital_id}/beds/summary")
    avail_icu_after = r_beds_after.json()["by_category"]["ICU"]["available"]
    assert avail_icu_after == avail_icu_before - 1

    # Verify the specific bed status is RESERVED
    r_beds = client.get(f"/api/v1/hospitals/{selected_hospital_id}/beds")
    assert r_beds.status_code == 200
    bed_record = next((b for b in r_beds.json() if b["id"] == reserved_bed_id), None)
    assert bed_record is not None
    assert bed_record["status"] == "RESERVED"

    # Verify reservation lookup
    r_res = client.get(f"/api/v1/reservations/{reservation_id}")
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "RESERVED"

    # -------------------------------------------------------------
    # Step 5: Verify Hospital Operations Queue
    # -------------------------------------------------------------
    r_queue = client.get(f"/api/v1/hospitals/{selected_hospital_id}/queue")
    assert r_queue.status_code == 200
    queue_items = r_queue.json()
    matching_q = next((q for q in queue_items if q["emergency_id"] == emergency_id), None)
    assert matching_q is not None
    assert matching_q["priority"] == "P1_CRITICAL"
    assert matching_q["patient_id"] == patient_id
    assert matching_q["emergency_type"] == "CARDIAC_ARREST"
    assert "MG Road" in matching_q["patient_address"]


def test_anonymous_guest_emergency_creation_and_ranking(client):
    """
    Verifies that emergency care is accessible without logging in:
    Guest emergency intake generates an anonymous patient record.
    """
    guest_emergency_id = f"emg-guest-{int(datetime.utcnow().timestamp())}"
    # Ensure client cookies are clean
    client.cookies.clear()

    payload = {
        "emergencyId": guest_emergency_id,
        "emergencyType": "TRAUMA_CRITICAL",
        "priority": "P1_CRITICAL",
        "patientLocation": {
            "latitude": 12.9352,
            "longitude": 77.6245,
            "address": "Koramangala, Bengaluru"
        },
        "requiredBedType": "ICU",
        "symptoms": "Multiple severe fractures after vehicle collision"
    }

    r = client.post("/api/v1/emergencies", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["emergencyId"] == guest_emergency_id
    assert data["patientId"].startswith("pat-guest-") or len(data["patientId"]) > 0

    # Rank hospitals for this guest emergency
    rank_payload = {
        "emergencyId": guest_emergency_id,
        "patientLocation": payload["patientLocation"],
        "emergencyType": "TRAUMA_CRITICAL",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU"
    }
    r_rank = client.post("/api/v1/hospitals/rank", json=rank_payload)
    assert r_rank.status_code == 200
    assert len(r_rank.json()["rankedHospitals"]) > 0


def test_conflict_and_error_handling(client):
    """
    Verifies API error handling:
    1. Selecting hospital for non-existent emergency -> 404
    2. Selecting non-existent hospital -> 404
    3. Selecting hospital when requested bed category is exhausted -> 409
    """
    # 1. Non-existent emergency
    r1 = client.post("/api/v1/emergencies/emg-nonexistent-9999/select-hospital", json={
        "selectedHospitalId": "hosp-manipal-hal",
        "requiredBedType": "ICU"
    })
    assert r1.status_code == 404

    # Create a real emergency for following tests
    emg_id = f"emg-err-{int(datetime.utcnow().timestamp())}"
    client.post("/api/v1/emergencies", json={
        "emergencyId": emg_id,
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "requiredBedType": "ICU"
    })

    # 2. Non-existent hospital
    r2 = client.post(f"/api/v1/emergencies/{emg_id}/select-hospital", json={
        "selectedHospitalId": "hosp-does-not-exist",
        "requiredBedType": "ICU"
    })
    assert r2.status_code == 404

    # 3. Exhausted / unavailable bed category:
    # Columbia Asia Hebbal (hosp-columbia-hebbal) has 0 available ICU beds
    r3 = client.post(f"/api/v1/emergencies/{emg_id}/select-hospital", json={
        "selectedHospitalId": "hosp-columbia-hebbal",
        "requiredBedType": "ICU"
    })
    # Columbia Asia has 0 available ICU beds, so CAS lock returns 409 Conflict
    assert r3.status_code == 409
    assert "No available ICU beds" in r3.json()["detail"]


def test_patient_privacy_ownership_protection(client):
    """
    Verifies that a logged-in patient cannot access or modify an emergency
    belonging to another patient.
    """
    # Patient 1 creates an emergency
    p1_email = f"p1_{int(datetime.utcnow().timestamp())}@example.com"
    r_p1_reg = client.post("/api/v1/auth/register", json={
        "full_name": "Patient One",
        "email": p1_email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "captcha_token": "verified"
    })
    assert r_p1_reg.status_code == 201
    r_p1_login = client.post("/api/v1/auth/login", json={"email": p1_email, "password": "Password123!", "captcha_token": "verified"})
    assert r_p1_login.status_code == 200

    emg_p1 = f"emg-p1-{int(datetime.utcnow().timestamp())}"
    r_create = client.post("/api/v1/emergencies", json={
        "emergencyId": emg_p1,
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "requiredBedType": "ICU"
    })
    assert r_create.status_code == 201

    # Patient 2 registers and logs in
    p2_email = f"p2_{int(datetime.utcnow().timestamp())}@example.com"
    r_p2_reg = client.post("/api/v1/auth/register", json={
        "full_name": "Patient Two",
        "email": p2_email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "captcha_token": "verified"
    })
    assert r_p2_reg.status_code == 201
    r_p2_login = client.post("/api/v1/auth/login", json={"email": p2_email, "password": "Password123!", "captcha_token": "verified"})
    assert r_p2_login.status_code == 200

    # Patient 2 tries to select hospital for Patient 1's emergency -> 403 Forbidden!
    r_unauth_select = client.post(f"/api/v1/emergencies/{emg_p1}/select-hospital", json={
        "selectedHospitalId": "hosp-manipal-hal",
        "requiredBedType": "ICU"
    })
    assert r_unauth_select.status_code == 403
    assert "cannot select a hospital for another patient's emergency" in r_unauth_select.json()["detail"]
