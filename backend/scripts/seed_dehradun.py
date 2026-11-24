
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "database" / "sirensync_hospital.db"

# These are prototype records based on the patient portal mock data.
# Bed counts are DEMO inventory, not verified live hospital capacity.

hospitals = [
    {
        "id": "hosp-max-ddn",
        "name": "Max Super Speciality Hospital",
        "address": "Mussoorie Diversion Road, Malsi, Dehradun",
        "latitude": 30.3737695,
        "longitude": 78.0748083,
        "contact": "+91 135 667 3000",
        "beds": {"ICU": 3, "TRAUMA_EMERGENCY": 8},
        "capabilities": [
            ("CARDIAC_CATH_LAB", "Cardiac care and catheterisation"),
            ("ICU_VENTILATOR", "Intensive care and ventilator support"),
            ("NEUROSURGERY", "Neurosurgical care"),
            ("TRAUMA_LEVEL_1", "Trauma emergency care"),
        ],
    },
    {
        "id": "hosp-synergy",
        "name": "Synergy Institute of Medical Sciences",
        "address": "Canal Road, Ballupur Chowk, Dehradun",
        "latitude": 30.3375992,
        "longitude": 78.0138545,
        "contact": "+91 135 222 6000",
        "beds": {"ICU": 5, "TRAUMA_EMERGENCY": 12},
        "capabilities": [
            ("CARDIAC_CATH_LAB", "Cardiac care"),
            ("ICU_VENTILATOR", "Critical care"),
        ],
    },
    {
        "id": "hosp-cmi",
        "name": "Combined Medical Institute (CMI Hospital)",
        "address": "Haridwar Road, Dharampur, Dehradun",
        "latitude": 30.3167914,
        "longitude": 78.0437622,
        "contact": "+91 135 265 4700",
        "beds": {"ICU": 2, "TRAUMA_EMERGENCY": 6},
        "capabilities": [
            ("TRAUMA_LEVEL_1", "Trauma care"),
            ("GENERAL_EMERGENCY", "General emergency care"),
        ],
    },
    {
        "id": "hosp-gdmc-ddn",
        "name": "Government Doon Medical College Hospital",
        "address": "New Road, Race Course, Dehradun",
        "latitude": 30.3196005,
        "longitude": 78.0422984,
        "contact": "+91 135 271 2100",
        "beds": {"ICU": 2, "TRAUMA_EMERGENCY": 15},
        "capabilities": [
            ("TRAUMA_LEVEL_1", "Trauma care"),
            ("GENERAL_EMERGENCY", "General emergency care"),
            ("BURN_CARE", "Burn care"),
        ],
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH)

    try:
        with conn:
            now = datetime.utcnow().isoformat(sep=" ")

            for hospital in hospitals:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO hospitals
                    (id, name, address, latitude, longitude,
                     contact_number, is_active, created_at, region)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, 'Dehradun')
                    """,
                    (
                        hospital["id"],
                        hospital["name"],
                        hospital["address"],
                        hospital["latitude"],
                        hospital["longitude"],
                        hospital["contact"],
                        now,
                    ),
                )

                for bed_type, count in hospital["beds"].items():
                    department = (
                        "Intensive Care"
                        if bed_type == "ICU"
                        else "Emergency"
                    )

                    for number in range(1, count + 1):
                        bed_id = (
                            f"{hospital['id']}-"
                            f"{bed_type.lower()}-{number:03d}"
                        )

                        conn.execute(
                            """
                            INSERT OR IGNORE INTO beds
                            (id, hospital_id, bed_number, bed_type,
                             status, department, version,
                             created_at, updated_at)
                            VALUES (?, ?, ?, ?, 'AVAILABLE', ?, 1, ?, ?)
                            """,
                            (
                                bed_id,
                                hospital["id"],
                                f"{bed_type}-{number:03d}",
                                bed_type,
                                department,
                                now,
                                now,
                            ),
                        )

                for code, description in hospital["capabilities"]:
                    exists = conn.execute(
                        """
                        SELECT 1 FROM hospital_capabilities
                        WHERE hospital_id = ? AND capability_code = ?
                        """,
                        (hospital["id"], code),
                    ).fetchone()

                    if not exists:
                        conn.execute(
                            """
                            INSERT INTO hospital_capabilities
                            (hospital_id, capability_code, description)
                            VALUES (?, ?, ?)
                            """,
                            (hospital["id"], code, description),
                        )

        print("Dehradun prototype hospital seeding completed.")

    finally:
        conn.close()


if __name__ == "__main__":
    seed()
