"""
plates.py – Number-plate logic for ANPR-based ambulance identification.
All functions are short and beginner-readable.
"""

import json
import pathlib
import re

# Registry path relative to project root
_DEFAULT_REGISTRY = pathlib.Path(__file__).parents[1] / "sample_data" / "ambulance_registry.json"


# Load ambulance registry from a JSON file
def load_registry(registry_path=None):
    """Return a list of registry dicts from the JSON file.
    Each dict has: plate, ambulance_id, operator, type, active.
    Replace this function body with an HTTP call to use the ambulance module's API.
    """
    path = pathlib.Path(registry_path) if registry_path else _DEFAULT_REGISTRY
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # JSON may be a list directly, or wrapped in {"registry": [...]}
    return data if isinstance(data, list) else data.get("registry", [])


# Normalise a raw OCR plate string to uppercase alphanumeric
def normalise_plate(raw_plate):
    """Strip non-alphanumeric chars and apply Indian-format-aware OCR fixes.

    Indian format: SS DD LLL DDDD  (S=state letter, D=digit, L=series letter)
    Example: KA 01 AB 1234

    OCR confusion fixes are applied position-by-position:
      - Positions 0-1 (state code, letters): 0→O, 1→I, 5→S, 8→B
      - Positions 2-3 (district digits):     O→0, I→1, S→5, B→8
      - Positions 4-6 (series letters):      0→O, 1→I, 5→S, 8→B
      - Positions 7-10 (registration digits):O→0, I→1, S→5, B→8
    """
    # Keep only uppercase letters and digits
    plate = re.sub(r"[^A-Z0-9]", "", raw_plate.upper())

    if len(plate) < 6:
        # Too short to apply format fixes — return as-is
        return plate

    result = list(plate)
    digit_to_letter = {"0": "O", "1": "I", "5": "S", "8": "B"}
    letter_to_digit = {"O": "0", "I": "1", "S": "5", "B": "8"}

    # Positions 0-1: expect letters (state code)
    for i in range(min(2, len(result))):
        result[i] = digit_to_letter.get(result[i], result[i])

    # Positions 2-3: expect digits (district code)
    for i in range(2, min(4, len(result))):
        result[i] = letter_to_digit.get(result[i], result[i])

    # Positions 4 to len-4: expect letters (series, 1-3 chars)
    series_end = max(4, len(result) - 4)
    for i in range(4, min(series_end, len(result))):
        result[i] = digit_to_letter.get(result[i], result[i])

    # Last 4 positions: expect digits (registration number)
    for i in range(max(0, len(result) - 4), len(result)):
        result[i] = letter_to_digit.get(result[i], result[i])

    return "".join(result)


# Check if two plate strings differ by at most 1 character
def fuzzy_match(candidate, target):
    """Return True if candidate and target are same length and differ by ≤1 character."""
    if len(candidate) != len(target):
        return False
    return sum(c1 != c2 for c1, c2 in zip(candidate, target)) <= 1


# Find a registry entry whose plate matches the candidate (exact or fuzzy)
def match_plate(normalised_plate, registry):
    """Return the matching registry entry or None.
    Skips inactive entries. Tries exact match first, then fuzzy (≤1 char diff).
    """
    for entry in registry:
        if not entry.get("active", True):
            continue
        reg_plate = normalise_plate(entry["plate"])
        if normalised_plate == reg_plate:
            return entry
    # Second pass: fuzzy only (avoid accepting a fuzzy when an exact exists elsewhere)
    for entry in registry:
        if not entry.get("active", True):
            continue
        reg_plate = normalise_plate(entry["plate"])
        if fuzzy_match(normalised_plate, reg_plate):
            return entry
    return None


# Crop the lower 30% of a vehicle bounding box as a rough plate region
def fallback_plate_crop(vehicle_bbox, frame):
    """Return a BGR crop of the plate area (lower 30% of the vehicle box).
    Used when no dedicated licence-plate detection model is available.
    NOTE: a pretrained LP detection model (e.g. WiderFace-based) would give better results.
    """
    x1, y1, x2, y2 = vehicle_bbox
    h = y2 - y1
    plate_y1 = y2 - int(0.30 * h)
    return frame[plate_y1:y2, x1:x2]
