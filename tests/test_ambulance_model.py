"""
Tests for Phase 1: Ambulance Data Model & Seed Fleet
Verifies that the Ambulance table, enums, relationships, and seed data
are properly initialized without compromising existing models or data.
"""
import pytest
from datetime import datetime
from backend.models.ambulance import Ambulance
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum
from backend.models.hospital import Hospital
from backend.models.emergency import Emergency
from backend.database.base import Base

def test_ambulance_metadata_registration():
    """Verify Ambulance model is registered in Base.metadata with expected schema."""
    assert "ambulances" in Base.metadata.tables
    table = Base.metadata.tables["ambulances"]

    column_names = {col.name for col in table.columns}
    expected_columns = {
        "id",
        "vehicle_number",
        "driver_name",
        "driver_contact",
        "ambulance_type",
        "equipment_tags",
        "status",
        "current_latitude",
        "current_longitude",
        "current_address",
        "assigned_emergency_id",
        "destination_hospital_id",
        "route_progress",
        "is_simulated",
        "version",
        "created_at",
        "updated_at",
    }
    assert expected_columns.issubset(column_names)

def test_ambulance_enums():
    """Verify AmbulanceStatusEnum and AmbulanceTypeEnum values."""
    assert AmbulanceStatusEnum.AVAILABLE.value == "AVAILABLE"
    assert AmbulanceStatusEnum.ASSIGNED.value == "ASSIGNED"
    assert AmbulanceStatusEnum.EN_ROUTE_PICKUP.value == "EN_ROUTE_PICKUP"
    assert AmbulanceStatusEnum.PATIENT_ONBOARD.value == "PATIENT_ONBOARD"
    assert AmbulanceStatusEnum.EN_ROUTE_HOSPITAL.value == "EN_ROUTE_HOSPITAL"
    assert AmbulanceStatusEnum.ARRIVED.value == "ARRIVED"
    assert AmbulanceStatusEnum.MAINTENANCE.value == "MAINTENANCE"

    assert AmbulanceTypeEnum.BLS.value == "BLS"
    assert AmbulanceTypeEnum.ALS.value == "ALS"
    assert AmbulanceTypeEnum.MICU.value == "MICU"

def test_seeded_ambulances_loaded(db_session):
    """Verify seeded ambulances are loaded into test database."""
    ambulances = db_session.query(Ambulance).all()
    assert len(ambulances) >= 8

    # Verify at least one of each type exists
    types = {amb.ambulance_type for amb in ambulances}
    assert AmbulanceTypeEnum.ALS in types
    assert AmbulanceTypeEnum.BLS in types
    assert AmbulanceTypeEnum.MICU in types

    # Verify available ambulances exist
    available = [amb for amb in ambulances if amb.status == AmbulanceStatusEnum.AVAILABLE]
    assert len(available) >= 5

    # Check specific seed record details
    amb1 = db_session.query(Ambulance).filter(Ambulance.id == "amb-bengaluru-als-01").first()
    assert amb1 is not None
    assert amb1.vehicle_number == "KA-01-EA-1081"
    assert amb1.driver_name == "Rajesh Kumar"
    assert "VENTILATOR" in amb1.equipment_tags
    assert amb1.is_simulated is True

def test_create_custom_ambulance(db_session):
    """Verify creating a custom Ambulance record persists correctly."""
    custom_amb = Ambulance(
        id="amb-test-phase1-custom",
        vehicle_number="KA-05-TEST-9999",
        driver_name="Test Driver",
        driver_contact="+91-99999-00000",
        ambulance_type=AmbulanceTypeEnum.MICU,
        equipment_tags="CUSTOM_EQUIPMENT,VENTILATOR",
        status=AmbulanceStatusEnum.AVAILABLE,
        current_latitude=12.9500,
        current_longitude=77.6000,
        current_address="Custom Test Location",
        route_progress=0.0,
        is_simulated=True,
        version=1,
        created_at=datetime.utcnow()
    )
    db_session.add(custom_amb)
    db_session.commit()

    retrieved = db_session.query(Ambulance).filter(Ambulance.id == "amb-test-phase1-custom").first()
    assert retrieved is not None
    assert retrieved.vehicle_number == "KA-05-TEST-9999"
    assert retrieved.ambulance_type == AmbulanceTypeEnum.MICU
    assert retrieved.status == AmbulanceStatusEnum.AVAILABLE

def test_existing_data_preserved(db_session):
    """Verify that adding the Ambulance model did not corrupt or alter existing models."""
    hospitals = db_session.query(Hospital).all()
    assert len(hospitals) == 5

    # Ensure hospital capabilities and beds are intact
    manipal = db_session.query(Hospital).filter(Hospital.id == "hosp-manipal-hal").first()
    assert manipal is not None
    assert len(manipal.beds) > 0
    assert len(manipal.capabilities) > 0
