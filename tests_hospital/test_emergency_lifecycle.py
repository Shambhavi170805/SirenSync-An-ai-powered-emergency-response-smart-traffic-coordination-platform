"""
Tests for Canonical Emergency Lifecycle & Patient Intake Integration
Covers:
1. Dedicated registration endpoint (POST /api/v1/emergencies)
2. Database persistence of symptoms, patient ID, priority, coordinates, bed type
3. Idempotent re-registration (200 OK) vs conflicting re-registration (409 Conflict)
4. Ranking validation against registered emergency (200 OK, 404 Not Found, 409 Conflict)
5. Hospital selection & reservation with authentic priority preservation (no placeholder downgrades)
6. Hospital queue linkage retaining patient ID, symptoms, priority, and address
7. Migration idempotence
"""
import pytest
from sqlalchemy import inspect
from tests_hospital.conftest import TestingSessionLocal
from backend.models.emergency import Emergency
from backend.models.reservation import BedReservation
from backend.models.queue import HospitalQueueItem
from backend.models.bed import Bed
from backend.models.hospital import Hospital
from backend.models.enums import PriorityEnum, BedTypeEnum, BedStatusEnum
from backend.services.bed_service import (
    BedManagementService,
    BedTypeMismatchException,
    BedNotAvailableException,
)
from backend.database.init_db import migrate_db
from backend.database.session import engine

def test_emergency_registration_success_and_get(client):
    emergency_id = "emg-test-life-001"
    patient_id = "pat-shambhavi-101"
    symptoms = "Sudden onset chest pain radiating to left arm, shortness of breath"

    payload = {
        "emergencyId": emergency_id,
        "patientId": patient_id,
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "patientLocation": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "Indiranagar 100ft Road, Bangalore"
        },
        "requiredBedType": "ICU",
        "symptoms": symptoms
    }

    # Register emergency
    res = client.post("/api/v1/emergencies", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["emergencyId"] == emergency_id
    assert data["patientId"] == patient_id
    assert data["emergencyType"] == "CARDIAC_ARREST"
    assert data["priority"] == "P1_CRITICAL"
    assert data["requiredBedType"] == "ICU"
    assert data["symptoms"] == symptoms
    assert data["patientLocation"]["latitude"] == 12.9716
    assert data["patientLocation"]["longitude"] == 77.5946
    assert data["patientLocation"]["address"] == "Indiranagar 100ft Road, Bangalore"
    assert data["selectedHospitalId"] is None

    # Fetch registered emergency
    res_get = client.get(f"/api/v1/emergencies/{emergency_id}")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["emergencyId"] == emergency_id
    assert get_data["patientId"] == patient_id
    assert get_data["symptoms"] == symptoms

    # Query directly from database session
    db = TestingSessionLocal()
    try:
        db_record = db.query(Emergency).filter(Emergency.id == emergency_id).first()
        assert db_record is not None
        assert db_record.patient_id == patient_id
        assert db_record.symptoms == symptoms
        assert db_record.priority == PriorityEnum.P1_CRITICAL
        assert db_record.required_bed_type == BedTypeEnum.ICU
        assert db_record.patient_latitude == 12.9716
    finally:
        db.close()

def test_emergency_get_not_found(client):
    res = client.get("/api/v1/emergencies/non-existent-emergency-xyz")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_emergency_duplicate_registration_idempotency(client):
    emergency_id = "emg-test-life-002"
    payload = {
        "emergencyId": emergency_id,
        "patientId": "pat-102",
        "emergencyType": "TRAUMA_CRITICAL",
        "priority": "P1_CRITICAL",
        "patientLocation": {
            "latitude": 12.9352,
            "longitude": 77.6245,
            "address": "Koramangala 5th Block"
        },
        "requiredBedType": "TRAUMA_EMERGENCY",
        "symptoms": "Multiple fractures, severe bleeding"
    }

    # First registration -> 201 Created
    res1 = client.post("/api/v1/emergencies", json=payload)
    assert res1.status_code == 201

    # Second registration with identical payload -> 200 OK (idempotent)
    res2 = client.post("/api/v1/emergencies", json=payload)
    assert res2.status_code == 200
    assert res2.json()["emergencyId"] == emergency_id

def test_emergency_duplicate_registration_conflict(client):
    emergency_id = "emg-test-life-003"
    payload1 = {
        "emergencyId": emergency_id,
        "patientId": "pat-103",
        "emergencyType": "RESPIRATORY_DISTRESS",
        "priority": "P2_EMERGENCY",
        "patientLocation": {
            "latitude": 12.9800,
            "longitude": 77.5900,
            "address": "Shivajinagar"
        },
        "requiredBedType": "OXYGEN_HDU",
        "symptoms": "Severe wheezing, hypoxia"
    }

    res1 = client.post("/api/v1/emergencies", json=payload1)
    assert res1.status_code == 201

    # Conflicting re-registration: different priority and requiredBedType
    conflicting_payload = dict(payload1)
    conflicting_payload["priority"] = "P1_CRITICAL"
    conflicting_payload["requiredBedType"] = "ICU"

    res2 = client.post("/api/v1/emergencies", json=conflicting_payload)
    assert res2.status_code == 409
    detail = res2.json()["detail"]
    assert "already registered with conflicting data" in detail
    assert "priority" in detail
    assert "requiredBedType" in detail

def test_ranking_rejects_unregistered_emergency(client):
    rank_payload = {
        "emergencyId": "emg-unregistered-999",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "Test Loc"},
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["CARDIAC_CATH_LAB"]
    }
    res = client.post("/api/v1/hospitals/rank", json=rank_payload)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_ranking_rejects_conflicting_payload_against_registered_emergency(client):
    emergency_id = "emg-test-life-004"
    # Register as P1_CRITICAL and ICU
    reg_payload = {
        "emergencyId": emergency_id,
        "patientId": "pat-104",
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "Test Loc"},
        "requiredBedType": "ICU",
        "symptoms": "Chest pain"
    }
    r_reg = client.post("/api/v1/emergencies", json=reg_payload)
    assert r_reg.status_code == 201

    # Rank with mismatched requiredBedType (GENERAL_WARD instead of ICU)
    rank_payload = {
        "emergencyId": emergency_id,
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "Test Loc"},
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "requiredBedType": "GENERAL_WARD",
        "requiredCapabilities": []
    }
    res = client.post("/api/v1/hospitals/rank", json=rank_payload)
    assert res.status_code == 409
    assert "conflicts with registered emergency" in res.json()["detail"]
    assert "requiredBedType" in res.json()["detail"]

def test_hospital_selection_rejects_unregistered_emergency(client):
    select_payload = {
        "selectedHospitalId": "hosp-apollo-bg",
        "requiredBedType": "ICU"
    }
    res = client.post("/api/v1/emergencies/emg-unregistered-select/select-hospital", json=select_payload)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    # Ensure no reservation was created
    db = TestingSessionLocal()
    try:
        orphan_res = db.query(BedReservation).filter(BedReservation.emergency_id == "emg-unregistered-select").first()
        assert orphan_res is None
        orphan_q = db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == "emg-unregistered-select").first()
        assert orphan_q is None
    finally:
        db.close()

def test_full_intake_to_queue_lifecycle_preserves_authentic_priority_and_symptoms(client):
    emergency_id = "emg-test-life-full-005"
    patient_id = "pat-critical-vip-99"
    symptoms = "Acute myocardial infarction with ST-elevation, cardiogenic shock"

    # Step 1: Register emergency
    reg_payload = {
        "emergencyId": emergency_id,
        "patientId": patient_id,
        "emergencyType": "CARDIAC_INFARCTION",
        "priority": "P1_CRITICAL",
        "patientLocation": {
            "latitude": 12.9300,
            "longitude": 77.6200,
            "address": "Koramangala Ring Road"
        },
        "requiredBedType": "ICU",
        "symptoms": symptoms
    }
    r_reg = client.post("/api/v1/emergencies", json=reg_payload)
    assert r_reg.status_code == 201

    # Step 2: Rank hospitals
    rank_payload = {
        "emergencyId": emergency_id,
        "patientLocation": {
            "latitude": 12.9300,
            "longitude": 77.6200,
            "address": "Koramangala Ring Road"
        },
        "emergencyType": "CARDIAC_INFARCTION",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
    }
    r_rank = client.post("/api/v1/hospitals/rank", json=rank_payload)
    assert r_rank.status_code == 200
    top_hosp_id = r_rank.json()["rankedHospitals"][0]["hospitalId"]

    # Step 3: Select hospital
    select_payload = {
        "selectedHospitalId": top_hosp_id,
        "requiredBedType": "ICU"
    }
    r_sel = client.post(f"/api/v1/emergencies/{emergency_id}/select-hospital", json=select_payload)
    assert r_sel.status_code == 201
    sel_data = r_sel.json()
    assert sel_data["status"] == "SUCCESS"
    assert sel_data["hospitalId"] == top_hosp_id
    assert sel_data["emergencyId"] == emergency_id

    # Verify hospital queue API returns the authentic priority and symptoms
    r_queue = client.get(f"/api/v1/hospitals/{top_hosp_id}/queue")
    assert r_queue.status_code == 200
    q_list = r_queue.json()
    matched_item = next((item for item in q_list if item["emergency_id"] == emergency_id), None)
    assert matched_item is not None
    assert matched_item["priority"] == "P1_CRITICAL"
    assert matched_item["patient_id"] == patient_id
    assert matched_item["symptoms"] == symptoms
    assert matched_item["emergency_type"] == "CARDIAC_INFARCTION"
    assert matched_item["patient_address"] == "Koramangala Ring Road"

    # Verify database directly
    db = TestingSessionLocal()
    try:
        emg_record = db.query(Emergency).filter(Emergency.id == emergency_id).one()
        assert emg_record.priority == PriorityEnum.P1_CRITICAL
        assert emg_record.symptoms == symptoms
        assert emg_record.selected_hospital_id == top_hosp_id

        q_record = db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emergency_id).one()
        assert q_record.priority == PriorityEnum.P1_CRITICAL
        assert q_record.emergency_id == emergency_id
    finally:
        db.close()

def test_database_migration_idempotence():
    # Calling migrate_db multiple times must execute safely and cleanly
    migrate_db(engine)
    migrate_db(engine)

    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("emergencies")]
    assert "symptoms" in columns
    assert "patient_id" in columns
    assert "required_bed_type" in columns
    assert "priority" in columns

def test_bed_reservation_rejects_bed_type_mismatch_with_409(client):
    """
    Regression Test:
    Ensures that when patient selects a hospital with a requiredBedType that does not
    match the emergency's registered required_bed_type:
    1. Returns HTTP 409 Conflict.
    2. Detail explains the bed type mismatch clearly.
    3. Emergency's selected_hospital_id remains None.
    4. Zero reservations or queue items are created.
    """
    emergency_id = "emg-test-mismatch-001"
    reg_payload = {
        "emergencyId": emergency_id,
        "patientId": "pat-mismatch-01",
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "requiredBedType": "ICU",
        "symptoms": "Severe chest pain"
    }
    r_reg = client.post("/api/v1/emergencies", json=reg_payload)
    assert r_reg.status_code == 201

    # Request reservation for GENERAL_WARD (emergency requires ICU)
    select_payload = {
        "selectedHospitalId": "hosp-apollo-bg",
        "requiredBedType": "GENERAL_WARD"
    }
    r_sel = client.post(f"/api/v1/emergencies/{emergency_id}/select-hospital", json=select_payload)
    assert r_sel.status_code == 409
    detail = r_sel.json()["detail"]
    assert "bed type mismatch" in detail.lower()
    assert "GENERAL_WARD" in detail
    assert "ICU" in detail

    # Verify database integrity: zero partial persistence
    db = TestingSessionLocal()
    try:
        emg = db.query(Emergency).filter(Emergency.id == emergency_id).one()
        assert emg.selected_hospital_id is None, "Emergency selected_hospital_id was partially mutated!"

        res = db.query(BedReservation).filter(BedReservation.emergency_id == emergency_id).first()
        assert res is None, "Orphan reservation was created upon failed reservation!"

        queue_item = db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emergency_id).first()
        assert queue_item is None, "Orphan queue item was created upon failed reservation!"
    finally:
        db.close()

def test_failed_reservation_leaves_zero_partial_persistence(client):
    """
    Regression Test:
    Ensures that service-level BedTypeMismatchException and BedNotAvailableException
    cleanly roll back and leave no partial changes to emergency, bed, reservation, or queue.
    """
    db = TestingSessionLocal()
    try:
        emergency_id = "emg-test-no-partial-002"
        emg = Emergency(
            id=emergency_id,
            patient_id="pat-no-partial-02",
            emergency_type="CARDIAC_ARREST",
            priority=PriorityEnum.P1_CRITICAL,
            patient_latitude=12.9716,
            patient_longitude=77.5946,
            patient_address="Test MG Road",
            required_bed_type=BedTypeEnum.ICU,
            symptoms="Acute arrest",
            selected_hospital_id=None
        )
        db.add(emg)
        db.commit()

        # 1. Attempt reservation with mismatched bed type (TRAUMA_EMERGENCY vs ICU)
        with pytest.raises(BedTypeMismatchException) as exc_info:
            BedManagementService.reserve_bed_atomically(
                db=db,
                hospital_id="hosp-apollo-bg",
                bed_type=BedTypeEnum.TRAUMA_EMERGENCY,
                emergency_id=emergency_id
            )
        assert "does not match registered emergency required bed type" in str(exc_info.value)

        # Verify emergency is still in clean state
        db.refresh(emg)
        assert emg.selected_hospital_id is None
        assert db.query(BedReservation).filter(BedReservation.emergency_id == emergency_id).first() is None
        assert db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emergency_id).first() is None

        # 2. Attempt reservation where no beds are available for that bed type at an empty dummy hospital
        dummy_hosp_id = "hosp-dummy-nobeds"
        dummy_hosp = Hospital(
            id=dummy_hosp_id,
            name="Dummy Zero Bed Hospital",
            address="Nowhere Road",
            latitude=12.9900,
            longitude=77.6000,
            contact_number="+91-80-0000-0000",
            is_active=True
        )
        db.add(dummy_hosp)
        db.commit()

        with pytest.raises(BedNotAvailableException):
            BedManagementService.reserve_bed_atomically(
                db=db,
                hospital_id=dummy_hosp_id,
                bed_type=BedTypeEnum.ICU,
                emergency_id=emergency_id
            )

        db.refresh(emg)
        assert emg.selected_hospital_id is None
        assert db.query(BedReservation).filter(BedReservation.emergency_id == emergency_id).first() is None
        assert db.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emergency_id).first() is None
    finally:
        db.close()
