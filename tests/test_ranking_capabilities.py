import pytest
from backend.services.ranking_service import HospitalRankingEngine
from backend.schemas.ranking import RankingRequest
from backend.shared.contracts import CoordinatesContract
from backend.models.enums import PriorityEnum, BedTypeEnum

def test_capability_selection_test_a_default(client):
    """
    Test A — Original/default selection:
    Select Cardiac Cath Lab and ICU Ventilator.
    Verify the request contains exactly those selected capabilities.
    """
    payload = {
        "emergencyId": "emg-cap-test-a",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "emergencyType": "CARDIAC_ARREST",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
    }
    response = client.post("/api/v1/hospitals/rank", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["requiredCapabilities"] == ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
    # Check that hospitals evaluate specifically for these capabilities
    top_hospital = data["rankedHospitals"][0]
    for matched_cap in top_hospital["breakdown"]["matchedCapabilities"]:
        assert matched_cap in ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
    assert "TRAUMA_LEVEL_1" not in top_hospital["breakdown"]["matchedCapabilities"]

def test_capability_selection_test_b_different(client):
    """
    Test B — Different selection:
    Select Trauma Center and Pediatric ICU.
    Verify the request contains exactly those capabilities and does NOT contain
    Cardiac Cath Lab or ICU Ventilator.
    """
    payload = {
        "emergencyId": "emg-cap-test-b",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "emergencyType": "TRAUMA_PEDIATRIC",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["TRAUMA_LEVEL_1", "PEDIATRIC_EMERGENCY"]
    }
    response = client.post("/api/v1/hospitals/rank", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must contain exactly the new selection
    assert data["requiredCapabilities"] == ["TRAUMA_LEVEL_1", "PEDIATRIC_EMERGENCY"]
    assert "CARDIAC_CATH_LAB" not in data["requiredCapabilities"]
    assert "ICU_VENTILATOR" not in data["requiredCapabilities"]

    # In our database, Apollo and Columbia Asia have both capabilities
    top_hosp = data["rankedHospitals"][0]
    assert "CARDIAC_CATH_LAB" not in top_hosp["breakdown"]["matchedCapabilities"]
    assert "ICU_VENTILATOR" not in top_hosp["breakdown"]["matchedCapabilities"]

def test_capability_selection_test_c_single(client):
    """
    Test C — Single capability:
    Select only Trauma Center.
    Verify required_capabilities contains only that single capability.
    No previously selected capability should remain.
    """
    payload = {
        "emergencyId": "emg-cap-test-c",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "emergencyType": "TRAUMA",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["TRAUMA_LEVEL_1"]
    }
    response = client.post("/api/v1/hospitals/rank", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["requiredCapabilities"] == ["TRAUMA_LEVEL_1"]
    assert len(data["requiredCapabilities"]) == 1
    assert "CARDIAC_CATH_LAB" not in data["requiredCapabilities"]
    assert "ICU_VENTILATOR" not in data["requiredCapabilities"]
    assert "PEDIATRIC_EMERGENCY" not in data["requiredCapabilities"]

def test_capability_selection_test_d_change_after_eval(client):
    """
    Test D — Change selection after evaluation:
    Evaluate once with Cardiac Cath Lab + ICU Ventilator.
    Then change the selection to Trauma Center and evaluate again.
    Verify the second API request reflects only the new selection.
    """
    # 1. First evaluation: Cardiac + ICU
    payload_1 = {
        "emergencyId": "emg-cap-test-d1",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "emergencyType": "CARDIAC",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
    }
    r1 = client.post("/api/v1/hospitals/rank", json=payload_1)
    assert r1.status_code == 200
    assert r1.json()["requiredCapabilities"] == ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]

    # 2. Second evaluation: Trauma Center only
    payload_2 = {
        "emergencyId": "emg-cap-test-d2",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "emergencyType": "TRAUMA",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["TRAUMA_LEVEL_1"]
    }
    r2 = client.post("/api/v1/hospitals/rank", json=payload_2)
    assert r2.status_code == 200
    d2 = r2.json()

    # The second response must NOT retain stale capabilities from evaluation 1
    assert d2["requiredCapabilities"] == ["TRAUMA_LEVEL_1"]
    assert "CARDIAC_CATH_LAB" not in d2["requiredCapabilities"]
    assert "ICU_VENTILATOR" not in d2["requiredCapabilities"]

def test_capability_selection_test_e_deselect_and_switch(client):
    """
    Test E — Deselect previously selected capabilities:
    Start with Cardiac Cath Lab + ICU Ventilator.
    Deselect both and select Pediatric ICU.
    Evaluate and verify deselected capabilities are completely absent.
    """
    payload = {
        "emergencyId": "emg-cap-test-e",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "emergencyType": "PEDIATRIC",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": ["PEDIATRIC_EMERGENCY"]
    }
    r = client.post("/api/v1/hospitals/rank", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert data["requiredCapabilities"] == ["PEDIATRIC_EMERGENCY"]
    assert "CARDIAC_CATH_LAB" not in data["requiredCapabilities"]
    assert "ICU_VENTILATOR" not in data["requiredCapabilities"]

def test_capability_selection_empty_handled_correctly(client):
    """
    Test F — Empty selection:
    All mandatory capabilities deselected.
    Verify required_capabilities = [] is handled cleanly without silently restoring defaults.
    """
    payload = {
        "emergencyId": "emg-cap-test-f",
        "patientLocation": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "emergencyType": "GENERAL_UNSPECIFIED",
        "priority": "P2_EMERGENCY",
        "requiredBedType": "ICU",
        "requiredCapabilities": []
    }
    r = client.post("/api/v1/hospitals/rank", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert data["requiredCapabilities"] == []
    # All hospitals should receive full baseline capability score (1.0)
    for h in data["rankedHospitals"]:
        assert h["breakdown"]["capabilityMatchScore"] == 1.0
        assert h["breakdown"]["matchedCapabilities"] == []
        assert h["breakdown"]["missingCapabilities"] == []

def test_capability_selection_snake_case_alias_support(client):
    """
    Test G — Contract compatibility:
    Verify that sending required_capabilities in snake_case is properly parsed.
    """
    payload = {
        "emergency_id": "emg-cap-test-g",
        "patient_location": {"latitude": 12.9716, "longitude": 77.5946, "address": "MG Road"},
        "emergency_type": "TRAUMA_PEDIATRIC",
        "priority": "P1_CRITICAL",
        "required_bed_type": "ICU",
        "required_capabilities": ["TRAUMA_CENTER", "PEDIATRIC_ICU"]
    }
    r = client.post("/api/v1/hospitals/rank", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert "TRAUMA_CENTER" in data["requiredCapabilities"]
    assert "PEDIATRIC_ICU" in data["requiredCapabilities"]
    # Check that aliases match the corresponding hospital capabilities
    top_hosp = data["rankedHospitals"][0]
    matched = top_hosp["breakdown"]["matchedCapabilities"]
    assert "TRAUMA_LEVEL_1" in matched
    assert "PEDIATRIC_EMERGENCY" in matched

def test_capability_selection_produces_different_rankings(db_session):
    """
    Test H — Ranking differential:
    Verify that changing from Cardiac Cath Lab + ICU Ventilator to
    Trauma Center + Pediatric ICU produces distinct hospital scores.
    """
    engine = HospitalRankingEngine()
    coords = CoordinatesContract(latitude=12.9716, longitude=77.5946, address="MG Road")

    req_cardiac = RankingRequest(
        emergencyId="emg-diff-1",
        patientLocation=coords,
        emergencyType="CARDIAC",
        priority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        requiredCapabilities=["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
    )
    res_cardiac = engine.rank_hospitals(db_session, req_cardiac)

    req_trauma = RankingRequest(
        emergencyId="emg-diff-2",
        patientLocation=coords,
        emergencyType="TRAUMA",
        priority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        requiredCapabilities=["TRAUMA_LEVEL_1", "PEDIATRIC_EMERGENCY"]
    )
    res_trauma = engine.rank_hospitals(db_session, req_trauma)

    # In cardiac, Fortis Cunningham has 100% capability match and is Rank 1
    # In trauma + pediatric, Fortis Cunningham has 0% match and is deemed INELIGIBLE (for P1)
    fortis_cardiac = next(h for h in res_cardiac.rankedHospitals if "fortis" in h.hospitalId)
    fortis_trauma = next(h for h in res_trauma.rankedHospitals if "fortis" in h.hospitalId)

    assert fortis_cardiac.breakdown.capabilityMatchScore == 1.0
    assert fortis_cardiac.isEligible is True

    assert fortis_trauma.breakdown.capabilityMatchScore == 0.0
    assert fortis_trauma.isEligible is False

    # Top hospital differs between the two selections
    assert res_cardiac.rankedHospitals[0].hospitalId != res_trauma.rankedHospitals[0].hospitalId
