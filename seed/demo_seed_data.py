"""
Realistic Demo & Evaluator Seed Data for SirenSync
Populates 5 major hospitals in Bengaluru with diverse locations,
clinical capabilities, bed allocations, and availability states.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.database.init_db import init_db
from backend.models.hospital import Hospital, HospitalCapability
from backend.models.bed import Bed
from backend.models.emergency import Emergency
from backend.models.reservation import BedReservation
from backend.models.queue import HospitalQueueItem
from backend.models.audit import ReassignmentAuditLog
from backend.models.enums import BedTypeEnum, BedStatusEnum, PriorityEnum, ReservationStatusEnum, QueueStatusEnum

HOSPITALS_DATA = [
    {
        "id": "hosp-manipal-hal",
        "name": "Manipal Hospital HAL Airport Road",
        "address": "98, HAL Old Airport Rd, Kodihalli, Bengaluru, Karnataka 560017",
        "latitude": 12.9592,
        "longitude": 77.6477,
        "contact_number": "+91-80-2502-4444",
        "capabilities": [
            ("CARDIAC_CATH_LAB", "24/7 Advanced Cardiac Catheterization & Angioplasty"),
            ("ICU_VENTILATOR", "Level-3 Medical/Surgical ICU with advanced mechanical ventilation"),
            ("TRAUMA_LEVEL_1", "Comprehensive Level-1 Poly-trauma and Emergency Resuscitation"),
            ("STROKE_UNIT", "Hyper-acute Stroke Care & Endovascular Thrombectomy"),
            ("BURN_CARE", "Dedicated Burn Resuscitation & Intensive Care Unit"),
        ],
        "bed_counts": {
            BedTypeEnum.ICU: {"available": 5, "reserved": 2, "occupied": 1},
            BedTypeEnum.TRAUMA_EMERGENCY: {"available": 6, "reserved": 2, "occupied": 2},
            BedTypeEnum.OXYGEN_HDU: {"available": 8, "reserved": 1, "occupied": 1},
            BedTypeEnum.GENERAL_WARD: {"available": 15, "reserved": 0, "occupied": 5},
            BedTypeEnum.PEDIATRIC_ICU: {"available": 4, "reserved": 0, "occupied": 1},
        }
    },
    {
        "id": "hosp-apollo-bg",
        "name": "Apollo Hospitals Bannerghatta Road",
        "address": "154, IIMB Post, Bannerghatta Rd, Bengaluru, Karnataka 560076",
        "latitude": 12.8942,
        "longitude": 77.5990,
        "contact_number": "+91-80-2630-4050",
        "capabilities": [
            ("CARDIAC_CATH_LAB", "Cardiothoracic Emergency & Interventional Cardiology"),
            ("ICU_VENTILATOR", "Multi-disciplinary Intensive Care Unit"),
            ("TRAUMA_LEVEL_1", "Level-1 Emergency & Trauma Care Centre"),
            ("NEUROSURGERY", "Emergency Craniotomy & Neuro-trauma Intensive Care"),
            ("PEDIATRIC_EMERGENCY", "24/7 Dedicated Pediatric Emergency Resuscitation"),
        ],
        "bed_counts": {
            # Single available ICU bed specifically designed for Contention / Scenario B
            BedTypeEnum.ICU: {"available": 1, "reserved": 3, "occupied": 2},
            BedTypeEnum.TRAUMA_EMERGENCY: {"available": 4, "reserved": 2, "occupied": 2},
            BedTypeEnum.OXYGEN_HDU: {"available": 6, "reserved": 1, "occupied": 1},
            BedTypeEnum.GENERAL_WARD: {"available": 12, "reserved": 0, "occupied": 3},
            BedTypeEnum.PEDIATRIC_ICU: {"available": 3, "reserved": 1, "occupied": 1},
        }
    },
    {
        "id": "hosp-fortis-cunningham",
        "name": "Fortis Hospital Cunningham Road",
        "address": "14, Cunningham Rd, Vasanth Nagar, Bengaluru, Karnataka 560052",
        "latitude": 12.9868,
        "longitude": 77.5975,
        "contact_number": "+91-80-4199-4444",
        "capabilities": [
            ("CARDIAC_CATH_LAB", "Emergency Primary PCI & Interventional Suite"),
            ("ICU_VENTILATOR", "Coronary Care Unit & Intensive Medical Care"),
            ("STROKE_UNIT", "Rapid Stroke Assessment & Thrombolysis Protocol"),
        ],
        "bed_counts": {
            BedTypeEnum.ICU: {"available": 2, "reserved": 2, "occupied": 2},
            BedTypeEnum.TRAUMA_EMERGENCY: {"available": 3, "reserved": 1, "occupied": 2},
            BedTypeEnum.OXYGEN_HDU: {"available": 5, "reserved": 1, "occupied": 2},
            BedTypeEnum.GENERAL_WARD: {"available": 10, "reserved": 0, "occupied": 2},
        }
    },
    {
        "id": "hosp-columbia-hebbal",
        "name": "Columbia Asia Hospital Hebbal",
        "address": "Bellary Rd, Kirloskar Business Park, Hebbal, Bengaluru, Karnataka 560024",
        "latitude": 13.0354,
        "longitude": 77.5898,
        "contact_number": "+91-80-6660-0666",
        "capabilities": [
            ("TRAUMA_LEVEL_1", "High-velocity Highway Trauma Resuscitation"),
            ("ICU_VENTILATOR", "Critical Care & Ventilatory Support"),
            ("PEDIATRIC_EMERGENCY", "Pediatric Intensive Care & Emergency"),
        ],
        "bed_counts": {
            # Zero available ICU beds to demonstrate ineligible filtering during severe bed shortages!
            BedTypeEnum.ICU: {"available": 0, "reserved": 3, "occupied": 3},
            BedTypeEnum.TRAUMA_EMERGENCY: {"available": 5, "reserved": 1, "occupied": 2},
            BedTypeEnum.OXYGEN_HDU: {"available": 4, "reserved": 2, "occupied": 2},
            BedTypeEnum.GENERAL_WARD: {"available": 8, "reserved": 0, "occupied": 2},
        }
    },
    {
        "id": "hosp-bowring-shivaji",
        "name": "Bowring and Lady Curzon Hospital",
        "address": "Lady Curzon Rd, Shivaji Nagar, Bengaluru, Karnataka 560001",
        "latitude": 12.9829,
        "longitude": 77.6047,
        "contact_number": "+91-80-2559-1362",
        "capabilities": [
            ("TRAUMA_LEVEL_1", "Government Tertiary Trauma Centre"),
            ("BURN_CARE", "Regional Burns Intensive Care Centre"),
            ("GENERAL_EMERGENCY", "High-capacity Public Emergency Receiving Ward"),
        ],
        "bed_counts": {
            BedTypeEnum.ICU: {"available": 4, "reserved": 1, "occupied": 3},
            BedTypeEnum.TRAUMA_EMERGENCY: {"available": 8, "reserved": 2, "occupied": 4},
            BedTypeEnum.OXYGEN_HDU: {"available": 12, "reserved": 2, "occupied": 4},
            BedTypeEnum.GENERAL_WARD: {"available": 25, "reserved": 0, "occupied": 5},
        }
    },
]

def seed_database(db: Session = None):
    """
    Seeds database with 5 Bengaluru hospitals, full capability matrix,
    and realistic bed distributions.
    """
    close_at_end = False
    if db is None:
        init_db()
        db = SessionLocal()
        close_at_end = True

    try:
        # Clear existing data in reverse order of foreign keys
        db.query(ReassignmentAuditLog).delete()
        db.query(BedReservation).delete()
        db.query(HospitalQueueItem).delete()
        db.query(Emergency).delete()
        db.query(Bed).delete()
        db.query(HospitalCapability).delete()
        db.query(Hospital).delete()
        db.commit()

        total_beds_created = 0

        for hdata in HOSPITALS_DATA:
            hospital = Hospital(
                id=hdata["id"],
                name=hdata["name"],
                address=hdata["address"],
                latitude=hdata["latitude"],
                longitude=hdata["longitude"],
                contact_number=hdata["contact_number"],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(hospital)
            db.flush()

            # Add capabilities
            for cap_code, cap_desc in hdata["capabilities"]:
                cap = HospitalCapability(
                    hospital_id=hospital.id,
                    capability_code=cap_code,
                    description=cap_desc
                )
                db.add(cap)

            # Add beds
            bed_index = 1
            for btype, counts in hdata["bed_counts"].items():
                for _ in range(counts["available"]):
                    bed = Bed(
                        id=f"bed-{hospital.id}-{btype.value[:3].lower()}-{bed_index:02d}",
                        hospital_id=hospital.id,
                        bed_number=f"{btype.value[:3]}-{bed_index:02d}",
                        bed_type=btype,
                        status=BedStatusEnum.AVAILABLE,
                        department=f"{btype.value} Department"
                    )
                    db.add(bed)
                    bed_index += 1
                    total_beds_created += 1

                for _ in range(counts["reserved"]):
                    bed_id = f"bed-{hospital.id}-{btype.value[:3].lower()}-{bed_index:02d}"
                    bed = Bed(
                        id=bed_id,
                        hospital_id=hospital.id,
                        bed_number=f"{btype.value[:3]}-{bed_index:02d}",
                        bed_type=btype,
                        status=BedStatusEnum.RESERVED,
                        department=f"{btype.value} Department"
                    )
                    db.add(bed)
                    db.flush()

                    # Create matching Emergency, BedReservation and Queue item
                    emg_id = f"emg-{hospital.id}-{bed_index:02d}"
                    priority_choice = PriorityEnum.P1_CRITICAL if bed_index % 3 == 0 else (PriorityEnum.P2_EMERGENCY if bed_index % 2 == 0 else PriorityEnum.P3_URGENT)
                    route_pct = 25.0 if bed_index % 2 == 0 else 60.0

                    emergency = Emergency(
                        id=emg_id,
                        patient_id=f"pat-{hospital.id}-{bed_index:02d}",
                        emergency_type="ACUTE_CARDIO_RESPIRATORY" if btype == BedTypeEnum.ICU else "EMERGENCY_TRAUMA",
                        priority=priority_choice,
                        patient_latitude=hospital.latitude + 0.015,
                        patient_longitude=hospital.longitude + 0.012,
                        patient_address="En route from transit sector",
                        required_bed_type=btype,
                        selected_hospital_id=hospital.id
                    )
                    db.add(emergency)
                    db.flush()

                    reservation = BedReservation(
                        id=f"res-{hospital.id}-{bed_index:02d}",
                        emergency_id=emg_id,
                        hospital_id=hospital.id,
                        bed_id=bed_id,
                        status=ReservationStatusEnum.RESERVED,
                        reserved_at=datetime.utcnow()
                    )
                    db.add(reservation)

                    queue_item = HospitalQueueItem(
                        id=f"qitem-{hospital.id}-{bed_index:02d}",
                        hospital_id=hospital.id,
                        emergency_id=emg_id,
                        priority=priority_choice,
                        status=QueueStatusEnum.EN_ROUTE,
                        route_progress=route_pct,
                        notes=f"Inbound transit for bed {bed.bed_number}"
                    )
                    db.add(queue_item)

                    bed_index += 1
                    total_beds_created += 1

                for _ in range(counts["occupied"]):
                    bed = Bed(
                        id=f"bed-{hospital.id}-{btype.value[:3].lower()}-{bed_index:02d}",
                        hospital_id=hospital.id,
                        bed_number=f"{btype.value[:3]}-{bed_index:02d}",
                        bed_type=btype,
                        status=BedStatusEnum.OCCUPIED,
                        department=f"{btype.value} Department"
                    )
                    db.add(bed)
                    bed_index += 1
                    total_beds_created += 1

        # Seed sample ReassignmentAuditLog records for prototype policy demonstration
        audit_sample_1 = ReassignmentAuditLog(
            id="audit-sample-01",
            event_id="evt-reassign-demo-01",
            displaced_emergency_id="emg-hosp-m-02",
            displacing_emergency_id="emg-demo-p1-99",
            displaced_priority=PriorityEnum.P3_URGENT,
            displacing_priority=PriorityEnum.P1_CRITICAL,
            previous_hospital_id="hosp-manipal-hal",
            previous_bed_id="bed-hosp-manipal-hal-icu-06",
            new_hospital_id="hosp-apollo-bg",
            new_bed_id="bed-hosp-apollo-bg-icu-01",
            route_progress=26.5,
            threshold=40.0,
            decision="REASSIGNMENT_APPROVED",
            reason="Priority escalation: P1_CRITICAL displaced P3_URGENT at 26.5% route progress (< 40.0% threshold).",
            created_at=datetime.utcnow()
        )
        db.add(audit_sample_1)

        audit_sample_2 = ReassignmentAuditLog(
            id="audit-sample-02",
            event_id="evt-reassign-demo-02",
            displaced_emergency_id="emg-hosp-m-03",
            displacing_emergency_id="emg-demo-p1-100",
            displaced_priority=PriorityEnum.P3_URGENT,
            displacing_priority=PriorityEnum.P1_CRITICAL,
            previous_hospital_id="hosp-manipal-hal",
            previous_bed_id="bed-hosp-manipal-hal-tra-07",
            new_hospital_id=None,
            new_bed_id=None,
            route_progress=68.0,
            threshold=40.0,
            decision="REASSIGNMENT_REJECTED",
            reason="Active reservation retained: ambulance has covered 68.0% of route (>= configurable prototype threshold of 40.0%).",
            created_at=datetime.utcnow()
        )
        db.add(audit_sample_2)

        db.commit()
        print(f"Successfully seeded {len(HOSPITALS_DATA)} hospitals and {total_beds_created} beds with linked reservations and queue items.")

    finally:
        if close_at_end:
            db.close()

if __name__ == "__main__":
    seed_database()
