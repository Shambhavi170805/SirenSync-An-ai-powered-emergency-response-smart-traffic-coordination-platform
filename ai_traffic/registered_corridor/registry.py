"""Allow-list of ambulance registrations synchronized from the fleet database."""

import json
import re
from pathlib import Path
from typing import Dict, Optional


def normalize_plate(value: str) -> str:
    """Ignore OCR spacing and punctuation while retaining letters and digits."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


class VehicleRegistry:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.by_plate: Dict[str, dict] = {
            normalize_plate(item["vehicle_number"]): item
            for item in data.get("vehicles", [])
        }

    def find_plate(self, observed: str) -> Optional[dict]:
        """Exact normalized plate match only; uncertain OCR never grants priority."""
        return self.by_plate.get(normalize_plate(observed))

    def matches(self, ambulance_id: str, vehicle_number: str) -> bool:
        record = self.find_plate(vehicle_number)
        return bool(record and record.get("ambulance_id") == ambulance_id)

    def list_public(self) -> list[dict]:
        return [
            {"ambulance_id": v["ambulance_id"], "vehicle_number": v["vehicle_number"], "label": v.get("label", "Ambulance")}
            for v in self.by_plate.values()
        ]
