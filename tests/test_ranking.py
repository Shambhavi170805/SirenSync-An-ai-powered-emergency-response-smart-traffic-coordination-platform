import pytest
from backend.services.ranking_service import calculate_haversine_distance, HospitalRankingEngine
from backend.services.traffic_provider import MockTrafficProvider
from backend.schemas.ranking import RankingRequest
from backend.shared.contracts import CoordinatesContract
from backend.models.enums import PriorityEnum, BedTypeEnum

def test_haversine_distance_accuracy():
    # MG Road Bangalore (12.9716, 77.5946) to Manipal Hospital HAL (12.9592, 77.6477)
    dist = calculate_haversine_distance(12.9716, 77.5946, 12.9592, 77.6477)
    assert 5.0 <= dist <= 6.5 # Approx 5.9 km great circle distance

def test_deterministic_ranking_structure(db_session):
    engine = HospitalRankingEngine()
    req = RankingRequest(
        emergencyId="emg-test-001",
        patientLocation=CoordinatesContract(
            latitude=12.9716,
            longitude=77.5946,
            address="MG Road, Bangalore"
        ),
        emergencyType="CARDIAC_ARREST",
        priority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        requiredCapabilities=["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
    )
    res = engine.rank_hospitals(db_session, req)

    assert res.emergencyId == "emg-test-001"
    assert res.totalHospitalsEvaluated >= 5
    assert len(res.rankedHospitals) >= 5

    # Check first ranked hospital has valid structure
    top = res.rankedHospitals[0]
    assert top.rank == 1
    assert top.compositeScore > 0.0
    assert top.breakdown.distanceKm > 0.0
    assert 0.0 <= top.breakdown.capabilityMatchScore <= 1.0
    assert top.breakdown.trafficCongestionFactor >= 1.0
    assert isinstance(top.breakdown.explanation, str)
    assert len(top.breakdown.explanation) > 20

def test_critical_priority_capability_matching(db_session):
    engine = HospitalRankingEngine()
    req = RankingRequest(
        emergencyId="emg-test-002",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946),
        emergencyType="CARDIAC_ARREST",
        priority=PriorityEnum.P1_CRITICAL,
        requiredBedType=BedTypeEnum.ICU,
        requiredCapabilities=["CARDIAC_CATH_LAB"]
    )
    res = engine.rank_hospitals(db_session, req)

    for hosp in res.rankedHospitals:
        if "CARDIAC_CATH_LAB" in hosp.breakdown.matchedCapabilities:
            assert hosp.breakdown.capabilityMatchScore == 1.0
        else:
            # P1 critical emergency cannot tolerate missing critical capability
            assert hosp.isEligible is False

def test_zero_bed_availability_ineligibility(db_session):
    engine = HospitalRankingEngine()
    # Columbia Asia was seeded with 0 available ICU beds
    req = RankingRequest(
        emergencyId="emg-test-003",
        patientLocation=CoordinatesContract(latitude=13.0354, longitude=77.5898),
        emergencyType="SEVERE_TRAUMA",
        priority=PriorityEnum.P2_EMERGENCY,
        requiredBedType=BedTypeEnum.ICU,
        requiredCapabilities=["TRAUMA_LEVEL_1"]
    )
    res = engine.rank_hospitals(db_session, req)

    columbia = next((h for h in res.rankedHospitals if h.hospitalId == "hosp-columbia-hebbal"), None)
    assert columbia is not None
    # Because 0 ICU beds are available, it must be marked ineligible
    assert columbia.isEligible is False
    assert columbia.breakdown.availableBedsCount == 0

def test_explainable_breakdown_transparency(db_session):
    engine = HospitalRankingEngine()
    req = RankingRequest(
        emergencyId="emg-test-004",
        patientLocation=CoordinatesContract(latitude=12.9716, longitude=77.5946),
        emergencyType="TRAUMA",
        priority=PriorityEnum.P3_URGENT,
        requiredBedType=BedTypeEnum.TRAUMA_EMERGENCY,
        requiredCapabilities=["TRAUMA_LEVEL_1"]
    )
    res = engine.rank_hospitals(db_session, req)
    top = res.rankedHospitals[0]

    # Verify breakdown text contains explicit factor descriptions
    explanation = top.breakdown.explanation
    assert "Distance:" in explanation
    assert "Capability Match:" in explanation
    assert "Traffic:" in explanation
    assert "Bed Availability:" in explanation

def test_missing_coordinates_validation(client):
    # Latitude out of bounds (> 90.0)
    payload = {
        "emergencyId": "emg-invalid",
        "patientLocation": {"latitude": 120.0, "longitude": 77.0},
        "emergencyType": "CARDIAC",
        "priority": "P1_CRITICAL",
        "requiredBedType": "ICU",
        "requiredCapabilities": []
    }
    response = client.post("/api/v1/hospitals/rank", json=payload)
    assert response.status_code == 422
