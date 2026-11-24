"""
Idempotent Ambulance Fleet Seeding Script for SirenSync
Populates the Dehradun demonstration ambulance fleet without modifying or duplicating existing records.
"""
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.models.ambulance import Ambulance
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum

AMBULANCES_FLEET_DATA: List[Dict[str, Any]] = [
    # --- Dehradun Emergency Corridor (Primary Demonstration Fleet) ---
    {
        "id": "amb-ddn-als-01",
        "vehicle_number": "UK-07-GA-1081",
        "driver_name": "Vikram Rawat (Demo Driver)",
        "driver_contact": "+91-94120-DEMO1 (Demo Contact)",
        "ambulance_type": AmbulanceTypeEnum.ALS,
        "equipment_tags": "VENTILATOR,DEFIBRILLATOR,OXYGEN,ECG",
        "status": AmbulanceStatusEnum.AVAILABLE,
        "current_latitude": 30.3255,
        "current_longitude": 78.0437,
        "current_address": "Clock Tower, Rajpur Road, Dehradun (Demo Station 1)",
    },
    {
        "id": "amb-ddn-als-02",
        "vehicle_number": "UK-07-GA-1082",
        "driver_name": "Amit Negi (Demo Driver)",
        "driver_contact": "+91-94120-DEMO2 (Demo Contact)",
        "ambulance_type": AmbulanceTypeEnum.ALS,
        "equipment_tags": "VENTILATOR,DEFIBRILLATOR,OXYGEN,ECG",
        "status": AmbulanceStatusEnum.AVAILABLE,
        "current_latitude": 30.3382,
        "current_longitude": 78.0163,
        "current_address": "Ballupur Chowk, GMS Road, Dehradun (Demo Station 2)",
    },
    {
        "id": "amb-ddn-bls-01",
        "vehicle_number": "UK-07-GA-1083",
        "driver_name": "Sunil Joshi (Demo Driver)",
        "driver_contact": "+91-94120-DEMO3 (Demo Contact)",
        "ambulance_type": AmbulanceTypeEnum.BLS,
        "equipment_tags": "OXYGEN,FIRST_AID_KIT,STRETCHER",
        "status": AmbulanceStatusEnum.AVAILABLE,
        "current_latitude": 30.3125,
        "current_longitude": 78.0465,
        "current_address": "Dharampur, Haridwar Road, Dehradun (Demo Station 3)",
    },
    {
        "id": "amb-ddn-micu-01",
        "vehicle_number": "UK-07-GA-1084",
        "driver_name": "Deepak Sharma (Demo Driver)",
        "driver_contact": "+91-94120-DEMO4 (Demo Contact)",
        "ambulance_type": AmbulanceTypeEnum.MICU,
        "equipment_tags": "FULL_ICU_VENTILATOR,VENTILATOR,DEFIBRILLATOR,INFUSION_PUMP,MULTIPARA_MONITOR,OXYGEN",
        "status": AmbulanceStatusEnum.AVAILABLE,
        "current_latitude": 30.3533,
        "current_longitude": 78.0642,
        "current_address": "Jakhan, Rajpur Road, Dehradun (Demo Station 4)",
    },
    {
        "id": "amb-ddn-bls-02",
        "vehicle_number": "UK-07-GA-1085",
        "driver_name": "Rohan Bisht (Demo Driver)",
        "driver_contact": "+91-94120-DEMO5 (Demo Contact)",
        "ambulance_type": AmbulanceTypeEnum.BLS,
        "equipment_tags": "OXYGEN,FIRST_AID_KIT,STRETCHER",
        "status": AmbulanceStatusEnum.AVAILABLE,
        "current_latitude": 30.3740,
        "current_longitude": 78.0750,
        "current_address": "Malsi, Mussoorie Diversion Road, Dehradun (Demo Station 5)",
    },
]

def seed_ambulances_idempotent(db: Session) -> int:
    """
    Seeds demonstration ambulance records idempotently.
    Inserts only if ambulance ID or vehicle number is not already registered.
    Never overwrites existing records or active assignments.
    Returns the number of newly inserted ambulances.
    """
    inserted_count = 0
    now = datetime.utcnow()

    for amb_data in AMBULANCES_FLEET_DATA:
        existing = (
            db.query(Ambulance)
            .filter(
                (Ambulance.id == amb_data["id"]) |
                (Ambulance.vehicle_number == amb_data["vehicle_number"])
            )
            .first()
        )
        if not existing:
            new_amb = Ambulance(
                id=amb_data["id"],
                vehicle_number=amb_data["vehicle_number"],
                driver_name=amb_data["driver_name"],
                driver_contact=amb_data["driver_contact"],
                ambulance_type=amb_data["ambulance_type"],
                equipment_tags=amb_data["equipment_tags"],
                status=amb_data["status"],
                current_latitude=amb_data["current_latitude"],
                current_longitude=amb_data["current_longitude"],
                current_address=amb_data["current_address"],
                assigned_emergency_id=None,
                destination_hospital_id=None,
                route_progress=0.0,
                is_simulated=True,
                version=1,
                created_at=now,
                updated_at=now
            )
            db.add(new_amb)
            inserted_count += 1

    if inserted_count > 0:
        db.commit()

    return inserted_count

if __name__ == "__main__":
    db = SessionLocal()
    try:
        count = seed_ambulances_idempotent(db)
        print(f"Idempotent ambulance fleet seeding complete: {count} new demo ambulances added.")
    finally:
        db.close()
