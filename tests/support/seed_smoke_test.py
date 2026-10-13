"""
Dedicated additive test-data helper for isolated smoke_test.db.

Strict safety guarantees:
1. Isolated exclusively to smoke_test.db; guarded against sirensync_hospital.db.
2. Independent engine and session lifecycle (no shared global engine or SessionLocal).
3. Non-destructive: strictly additive inserts; no drop, delete, truncate, or reset logic.
4. Idempotent: checks for pre-existing records and skips duplicate insertions.
5. Fails immediately on unexpected data conflicts.
6. Guaranteed resource cleanup: engine and session disposed under nested try/finally blocks.
"""

from pathlib import Path
import sys
from typing import Optional
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Import all domain models to ensure complete SQLAlchemy mapper/relationship registration
from backend.database.base import Base
from backend.models.hospital import Hospital, HospitalCapability
from backend.models.bed import Bed
from backend.models.emergency import Emergency
from backend.models.reservation import BedReservation
from backend.models.queue import HospitalQueueItem
from backend.models.ambulance import Ambulance
from backend.models.enums import (
    BedTypeEnum,
    BedStatusEnum,
    PriorityEnum,
    QueueStatusEnum,
    AmbulanceStatusEnum,
    AmbulanceTypeEnum,
)


def get_smoke_test_db_path() -> Path:
    """Resolve and validate the absolute path to smoke_test.db."""
    # tests/support/seed_smoke_test.py -> parent: tests/support -> parent: tests -> parent: project_root
    project_root = Path(__file__).resolve().parent.parent.parent
    db_path = (project_root / "smoke_test.db").resolve()

    # Explicit safety guards
    assert db_path.name == "smoke_test.db", f"Target DB filename must be smoke_test.db, got: {db_path.name}"
    assert "sirensync_hospital.db" not in str(db_path), "CRITICAL: Path guard triggered - cannot touch sirensync_hospital.db"
    assert db_path == (project_root / "smoke_test.db").resolve(), "CRITICAL: Path resolution mismatch"

    return db_path


def seed_smoke_test_data() -> dict:
    """
    Additively populate smoke_test.db with the minimal records required
    for Member 3 (Ambulance Coordination & Tracking) demonstration.
    """
    db_path = get_smoke_test_db_path()
    db_uri = f"sqlite:///{db_path}"

    print(f"[Smoke Seed] Binding dedicated engine to: {db_uri}")
    engine = create_engine(
        db_uri,
        echo=False,
        connect_args={"timeout": 15},  # Generous SQLite busy timeout to avoid lock contention
    )

    session: Optional[Session] = None
    inserted_summary = {
        "hospitals": 0,
        "beds": 0,
        "emergencies": 0,
        "queue_items": 0,
        "ambulances": 0,
    }

    try:
        # 0. Ensure tables exist without modifying or dropping any existing tables
        Base.metadata.create_all(bind=engine)

        LocalSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = LocalSession()

        try:
            # 1. Hospitals (2 test facilities)
            planned_hospitals = [
                Hospital(
                    id="hosp-smoke-manipal",
                    name="Manipal Hospital (Smoke Test)",
                    address="98 HAL Old Airport Rd, Kodihalli, Bengaluru",
                    latitude=12.9592,
                    longitude=77.6534,
                    contact_number="+91-80-2502-4444",
                    is_active=True,
                ),
                Hospital(
                    id="hosp-smoke-apollo",
                    name="Apollo Hospital (Smoke Test)",
                    address="154/11 Bannerghatta Rd, Bengaluru",
                    latitude=12.8936,
                    longitude=77.5973,
                    contact_number="+91-80-2630-4050",
                    is_active=True,
                ),
            ]

            for hosp in planned_hospitals:
                existing = session.get(Hospital, hosp.id)
                if existing:
                    # Validate all critical fields required for smoke-test dataset
                    if existing.name != hosp.name:
                        raise ValueError(f"Conflicting hospital found for ID '{hosp.id}': name '{existing.name}' != '{hosp.name}'")
                    if abs(existing.latitude - hosp.latitude) > 0.0001 or abs(existing.longitude - hosp.longitude) > 0.0001:
                        raise ValueError(f"Conflicting coordinates for hospital ID '{hosp.id}'")
                    if existing.is_active != hosp.is_active:
                        raise ValueError(f"Conflicting is_active status for hospital ID '{hosp.id}'")
                    print(f"[Smoke Seed] Hospital '{hosp.id}' already exists and matches expected state. Skipping.")
                else:
                    session.add(hosp)
                    inserted_summary["hospitals"] += 1
                    print(f"[Smoke Seed] Added hospital '{hosp.id}'.")

            session.flush()

            # 2. Beds (2 available ICU beds associated with the hospitals)
            planned_beds = [
                Bed(
                    id="bed-smoke-manipal-icu-01",
                    hospital_id="hosp-smoke-manipal",
                    bed_number="ICU-SMOKE-01",
                    bed_type=BedTypeEnum.ICU,
                    status=BedStatusEnum.AVAILABLE,
                    department="Intensive Care Unit",
                    version=1,
                ),
                Bed(
                    id="bed-smoke-apollo-icu-01",
                    hospital_id="hosp-smoke-apollo",
                    bed_number="ICU-SMOKE-02",
                    bed_type=BedTypeEnum.ICU,
                    status=BedStatusEnum.AVAILABLE,
                    department="Intensive Care Unit",
                    version=1,
                ),
            ]

            for bed in planned_beds:
                existing = session.get(Bed, bed.id)
                if existing:
                    # Validate all critical fields: hospital association, bed type, availability, bed number
                    if existing.hospital_id != bed.hospital_id:
                        raise ValueError(f"Conflicting bed hospital_id for ID '{bed.id}': '{existing.hospital_id}' != '{bed.hospital_id}'")
                    if existing.bed_type != bed.bed_type:
                        raise ValueError(f"Conflicting bed_type for bed ID '{bed.id}': '{existing.bed_type}' != '{bed.bed_type}'")
                    if existing.status != bed.status:
                        raise ValueError(f"Conflicting status for bed ID '{bed.id}': '{existing.status}' != '{bed.status}' (expected AVAILABLE)")
                    if existing.bed_number != bed.bed_number:
                        raise ValueError(f"Conflicting bed_number for bed ID '{bed.id}': '{existing.bed_number}' != '{bed.bed_number}'")
                    print(f"[Smoke Seed] Bed '{bed.id}' already exists and matches expected state. Skipping.")
                else:
                    session.add(bed)
                    inserted_summary["beds"] += 1
                    print(f"[Smoke Seed] Added bed '{bed.id}'.")

            session.flush()

            # 3. Emergency (1 test emergency with synthetic, non-PII identifier)
            planned_emergency = Emergency(
                id="emg-smoke-001",
                patient_id="synthetic-pt-smoke-001",
                emergency_type="CARDIAC",
                priority=PriorityEnum.P2_EMERGENCY,
                patient_latitude=12.9716,
                patient_longitude=77.5946,
                patient_address="MG Road Junction, Bengaluru (Synthetic Test Location)",
                required_bed_type=BedTypeEnum.ICU,
                selected_hospital_id="hosp-smoke-manipal",
            )

            existing_emg = session.get(Emergency, planned_emergency.id)
            if existing_emg:
                # Validate key relationships and required states
                if existing_emg.patient_id != planned_emergency.patient_id:
                    raise ValueError(f"Conflicting patient_id for emergency ID '{planned_emergency.id}': '{existing_emg.patient_id}' != '{planned_emergency.patient_id}'")
                if existing_emg.priority != planned_emergency.priority:
                    raise ValueError(f"Conflicting priority for emergency ID '{planned_emergency.id}': '{existing_emg.priority}' != '{planned_emergency.priority}'")
                if existing_emg.required_bed_type != planned_emergency.required_bed_type:
                    raise ValueError(f"Conflicting required_bed_type for emergency ID '{planned_emergency.id}': '{existing_emg.required_bed_type}' != '{planned_emergency.required_bed_type}'")
                if existing_emg.selected_hospital_id != planned_emergency.selected_hospital_id:
                    raise ValueError(f"Conflicting selected_hospital_id for emergency ID '{planned_emergency.id}': '{existing_emg.selected_hospital_id}' != '{planned_emergency.selected_hospital_id}'")
                print(f"[Smoke Seed] Emergency '{planned_emergency.id}' already exists and matches expected state. Skipping.")
            else:
                session.add(planned_emergency)
                inserted_summary["emergencies"] += 1
                print(f"[Smoke Seed] Added emergency '{planned_emergency.id}'.")

            session.flush()

            # 4. Hospital Queue Item (1 corresponding queue item)
            planned_queue_item = HospitalQueueItem(
                id="qitem-smoke-001",
                hospital_id="hosp-smoke-manipal",
                emergency_id="emg-smoke-001",
                priority=PriorityEnum.P2_EMERGENCY,
                status=QueueStatusEnum.DISPATCHED,
                route_progress=25.0,
                notes="Member 3 Smoke Test - Dispatched Ambulance",
            )

            existing_qi = session.get(HospitalQueueItem, planned_queue_item.id)
            if existing_qi:
                # Validate key relationships and required states
                if existing_qi.emergency_id != planned_queue_item.emergency_id:
                    raise ValueError(f"Conflicting emergency_id for queue item '{planned_queue_item.id}': '{existing_qi.emergency_id}' != '{planned_queue_item.emergency_id}'")
                if existing_qi.hospital_id != planned_queue_item.hospital_id:
                    raise ValueError(f"Conflicting hospital_id for queue item '{planned_queue_item.id}': '{existing_qi.hospital_id}' != '{planned_queue_item.hospital_id}'")
                if existing_qi.priority != planned_queue_item.priority:
                    raise ValueError(f"Conflicting priority for queue item '{planned_queue_item.id}': '{existing_qi.priority}' != '{planned_queue_item.priority}'")
                if existing_qi.status != planned_queue_item.status:
                    raise ValueError(f"Conflicting status for queue item '{planned_queue_item.id}': '{existing_qi.status}' != '{planned_queue_item.status}'")
                print(f"[Smoke Seed] Queue item '{planned_queue_item.id}' already exists and matches expected state. Skipping.")
            else:
                # Check unique emergency_id constraint on queue items
                conflict_qi = session.execute(
                    select(HospitalQueueItem).where(HospitalQueueItem.emergency_id == planned_queue_item.emergency_id)
                ).scalar_one_or_none()
                if conflict_qi and conflict_qi.id != planned_queue_item.id:
                    raise ValueError(f"Queue item conflict: emergency '{planned_queue_item.emergency_id}' already in queue under item '{conflict_qi.id}'")
                session.add(planned_queue_item)
                inserted_summary["queue_items"] += 1
                print(f"[Smoke Seed] Added queue item '{planned_queue_item.id}'.")

            session.flush()

            # 5. Ambulances (1 assigned, 1 available standby)
            planned_ambulances = [
                Ambulance(
                    id="amb-smoke-als-01",
                    vehicle_number="KA-01-SMOKE-1081",
                    driver_name="Smoke Test Driver 1",
                    driver_contact="+91-90000-00001",
                    ambulance_type=AmbulanceTypeEnum.ALS,
                    equipment_tags="ventilator,defibrillator,oxygen",
                    status=AmbulanceStatusEnum.EN_ROUTE_HOSPITAL,
                    current_latitude=12.9650,
                    current_longitude=77.6200,
                    current_address="Intermediate Test Waypoint",
                    assigned_emergency_id="emg-smoke-001",
                    destination_hospital_id="hosp-smoke-manipal",
                    route_progress=25.0,
                    is_simulated=True,
                    version=1,
                ),
                Ambulance(
                    id="amb-smoke-bls-01",
                    vehicle_number="KA-01-SMOKE-1082",
                    driver_name="Smoke Test Driver 2",
                    driver_contact="+91-90000-00002",
                    ambulance_type=AmbulanceTypeEnum.BLS,
                    equipment_tags="basic_first_aid,oxygen",
                    status=AmbulanceStatusEnum.AVAILABLE,
                    current_latitude=12.8936,
                    current_longitude=77.5973,
                    current_address="Apollo Hospital Base (Standby)",
                    assigned_emergency_id=None,
                    destination_hospital_id=None,
                    route_progress=0.0,
                    is_simulated=True,
                    version=1,
                ),
            ]

            for amb in planned_ambulances:
                existing_amb = session.get(Ambulance, amb.id)
                if existing_amb:
                    # Validate all critical fields according to role:
                    if existing_amb.vehicle_number != amb.vehicle_number:
                        raise ValueError(f"Conflicting vehicle_number for ambulance '{amb.id}': '{existing_amb.vehicle_number}' != '{amb.vehicle_number}'")
                    if existing_amb.status != amb.status:
                        raise ValueError(f"Conflicting status for ambulance '{amb.id}': '{existing_amb.status}' != '{amb.status}'")
                    if existing_amb.assigned_emergency_id != amb.assigned_emergency_id:
                        raise ValueError(f"Conflicting assigned_emergency_id for ambulance '{amb.id}': '{existing_amb.assigned_emergency_id}' != '{amb.assigned_emergency_id}'")
                    if existing_amb.destination_hospital_id != amb.destination_hospital_id:
                        raise ValueError(f"Conflicting destination_hospital_id for ambulance '{amb.id}': '{existing_amb.destination_hospital_id}' != '{amb.destination_hospital_id}'")
                    if abs(existing_amb.route_progress - amb.route_progress) > 0.1:
                        raise ValueError(f"Conflicting route_progress for ambulance '{amb.id}': {existing_amb.route_progress} != {amb.route_progress}")
                    print(f"[Smoke Seed] Ambulance '{amb.id}' already exists and matches expected state. Skipping.")
                else:
                    # Check unique vehicle_number constraint
                    conflict_veh = session.execute(
                        select(Ambulance).where(Ambulance.vehicle_number == amb.vehicle_number)
                    ).scalar_one_or_none()
                    if conflict_veh:
                        raise ValueError(f"Conflicting ambulance vehicle_number '{amb.vehicle_number}' already in use by ID '{conflict_veh.id}'")

                    # Check unique assigned_emergency_id constraint if assigned
                    if amb.assigned_emergency_id:
                        conflict_emg_amb = session.execute(
                            select(Ambulance).where(Ambulance.assigned_emergency_id == amb.assigned_emergency_id)
                        ).scalar_one_or_none()
                        if conflict_emg_amb:
                            raise ValueError(f"Conflicting ambulance dispatch: emergency '{amb.assigned_emergency_id}' already assigned to ambulance '{conflict_emg_amb.id}'")

                    session.add(amb)
                    inserted_summary["ambulances"] += 1
                    print(f"[Smoke Seed] Added ambulance '{amb.id}'.")

            # Commit transactions safely
            session.commit()
            print(f"[Smoke Seed] Successfully committed additions: {inserted_summary}")
            return inserted_summary

        except Exception as exc:
            if session is not None:
                session.rollback()
            print(f"[Smoke Seed ERROR] Transaction rolled back due to error: {exc}", file=sys.stderr)
            raise
        finally:
            if session is not None:
                session.close()
                print("[Smoke Seed] Session closed.")

    finally:
        engine.dispose()
        print("[Smoke Seed] Engine disposed.")


if __name__ == "__main__":
    seed_smoke_test_data()
