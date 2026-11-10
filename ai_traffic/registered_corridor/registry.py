"""Local allow-list of ambulance registrations for the standalone traffic module."""

import json
import re
import threading
from pathlib import Path
from typing import Dict, Optional


def normalize_plate(value: str) -> str:
    """Ignore OCR spacing and punctuation while retaining letters and digits."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


class VehicleRegistry:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self._lock = threading.RLock()
        self.by_plate: Dict[str, dict] = {
            normalize_plate(item["vehicle_number"]): item
            for item in data.get("vehicles", [])
        }

    def find_plate(self, observed: str) -> Optional[dict]:
        """Exact normalized plate match only; uncertain OCR never grants priority."""
        with self._lock:
            record = self.by_plate.get(normalize_plate(observed))
            return dict(record) if record else None

    def matches(self, ambulance_id: str, vehicle_number: str) -> bool:
        record = self.find_plate(vehicle_number)
        if not record or record.get("ambulance_id") != ambulance_id or record.get("active") is False:
            return False
        status = str(record.get("status") or "").upper()
        return not status or status in {
            "ASSIGNED", "EN_ROUTE_PICKUP", "PATIENT_ONBOARD", "EN_ROUTE_HOSPITAL"
        }

    def sync_from_ambulance_api(self, ambulance: dict) -> dict:
        """Refresh one allow-list entry from Nidhi's fleet API response."""
        ambulance_id = str(ambulance.get("id") or ambulance.get("ambulanceId") or "").strip()
        vehicle_number = ambulance.get("vehicleNumber") or ambulance.get("vehicle_number") or ""
        plate = normalize_plate(vehicle_number)
        if not ambulance_id or not plate:
            raise ValueError("Ambulance API record must include id and vehicleNumber")

        # Remove stale plate entries for this ambulance before replacing its record.
        record = {
            "ambulance_id": ambulance_id,
            "vehicle_number": plate,
            "label": ambulance.get("ambulanceType") or "Ambulance",
            "active": True,
            "is_simulated": ambulance.get("isSimulated", ambulance.get("is_simulated", True)),
            "emergency_id": ambulance.get("assignedEmergencyId") or ambulance.get("emergencyId"),
            "status": ambulance.get("status"),
        }
        with self._lock:
            for key, existing in list(self.by_plate.items()):
                if existing.get("ambulance_id") == ambulance_id:
                    del self.by_plate[key]
            self.by_plate[plate] = record
        return record

    def list_public(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "ambulance_id": v["ambulance_id"],
                    "vehicle_number": v["vehicle_number"],
                    "label": v.get("label", "Ambulance"),
                    "status": v.get("status", "LOCAL_SAMPLE"),
                }
                for v in self.by_plate.values()
            ]
