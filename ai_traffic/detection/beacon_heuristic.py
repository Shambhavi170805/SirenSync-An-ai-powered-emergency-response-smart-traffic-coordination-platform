"""
Emergency Vehicle Beacon and Color Heuristic.
Used when custom fine-tuned YOLO weights are absent to distinguish ambulances from regular
traffic by analyzing high-intensity flashing strobes (red & blue) and emergency vehicle markings.
"""

from typing import Dict, Tuple
import cv2
import numpy as np

from ai_traffic.core.config import HeuristicConfig


class BeaconColorHeuristic:
    """
    Analyzes cropped vehicle bounding boxes for emergency beacon strobe signatures and colors.
    """

    def __init__(self, config: HeuristicConfig):
        self.config = config

    def analyze_vehicle(self, vehicle_crop: np.ndarray) -> Tuple[bool, float, Dict[str, float]]:
        """
        Analyzes a vehicle bounding box crop.

        Returns:
            Tuple of:
            - is_emergency (bool): True if heuristic thresholds are satisfied.
            - confidence (float): Computed confidence score between 0.0 and 1.0.
            - metrics (dict): Breakdown of red, blue, beacon cluster, and white body metrics.
        """
        if vehicle_crop is None or vehicle_crop.size == 0:
            return False, 0.0, {}

        h, w, _ = vehicle_crop.shape
        if h < 20 or w < 20:
            return False, 0.0, {}

        total_pixels = float(h * w)

        # Convert to HSV color space for lighting-invariant color thresholding
        hsv = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2HSV)

        # 1. Red Strobe Mask (wraps around 0/180 hue)
        red_lower1 = np.array([self.config.red_hue_range_1[0], self.config.min_saturation, self.config.min_value])
        red_upper1 = np.array([self.config.red_hue_range_1[1], 255, 255])
        red_lower2 = np.array([self.config.red_hue_range_2[0], self.config.min_saturation, self.config.min_value])
        red_upper2 = np.array([self.config.red_hue_range_2[1], 255, 255])

        mask_red1 = cv2.inRange(hsv, red_lower1, red_upper1)
        mask_red2 = cv2.inRange(hsv, red_lower2, red_upper2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        red_ratio = float(np.count_nonzero(mask_red)) / total_pixels

        # 2. Blue Strobe Mask
        blue_lower = np.array([self.config.blue_hue_range[0], self.config.min_saturation, self.config.min_value])
        blue_upper = np.array([self.config.blue_hue_range[1], 255, 255])
        mask_blue = cv2.inRange(hsv, blue_lower, blue_upper)
        blue_ratio = float(np.count_nonzero(mask_blue)) / total_pixels

        # 3. White Body Analysis (Ambulances typically have prominent white chassis)
        # White in HSV: low saturation (S < 40), high value (V > 180)
        white_lower = np.array([0, 0, 180])
        white_upper = np.array([180, 50, 255])
        mask_white = cv2.inRange(hsv, white_lower, white_upper)
        white_ratio = float(np.count_nonzero(mask_white)) / total_pixels

        # 4. Beacon Cluster Density on Roof (top 40% of vehicle height)
        roof_crop_h = max(5, int(h * 0.40))
        roof_red = mask_red[:roof_crop_h, :]
        roof_blue = mask_blue[:roof_crop_h, :]
        roof_pixels = float(roof_crop_h * w)

        roof_beacon_pixels = np.count_nonzero(roof_red) + np.count_nonzero(roof_blue)
        roof_beacon_ratio = float(roof_beacon_pixels) / roof_pixels

        # Scoring Logic:
        # Emergency strobe beacons produce concentrated red/blue pixels near the roof/grille.
        score = 0.0

        # Roof beacon presence is the strongest indicator
        if roof_beacon_ratio > 0.015:
            score += 0.45
        elif roof_beacon_ratio > 0.005:
            score += 0.25

        # Both red and blue beacons present simultaneously (or alternating strobes)
        if red_ratio > 0.008 and blue_ratio > 0.008:
            score += 0.35
        elif red_ratio > 0.012 or blue_ratio > 0.012:
            score += 0.20

        # White chassis characteristic
        if white_ratio > 0.25:
            score += 0.20
        elif white_ratio > 0.15:
            score += 0.10

        confidence = min(0.95, round(score, 3))
        is_emergency = confidence >= 0.48

        metrics = {
            "red_ratio": round(red_ratio, 4),
            "blue_ratio": round(blue_ratio, 4),
            "roof_beacon_ratio": round(roof_beacon_ratio, 4),
            "white_ratio": round(white_ratio, 4),
            "heuristic_confidence": confidence
        }

        return is_emergency, confidence, metrics
