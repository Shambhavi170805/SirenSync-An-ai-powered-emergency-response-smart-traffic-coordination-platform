"""
Unit Tests for Computer Vision Components: Temporal Smoothing, Beacon Heuristic, and IoU.
"""

import numpy as np
import pytest
from ai_traffic.core.config import DetectionConfig, HeuristicConfig
from ai_traffic.detection.beacon_heuristic import BeaconColorHeuristic
from ai_traffic.detection.tracker import TemporalSmoothingTracker, calculate_iou
from ai_traffic.detection.yolo_detector import EmergencyVehicleDetector


def test_iou_calculation():
    box1 = [10, 10, 50, 50]  # area = 40*40 = 1600
    box2 = [30, 30, 70, 70]  # overlap = 20*20 = 400
    iou = calculate_iou(box1, box2)
    assert 0.14 < iou < 0.16

    # Disjoint boxes
    box3 = [100, 100, 120, 120]
    assert calculate_iou(box1, box3) == 0.0


def test_temporal_smoothing_tracker_requires_consecutive_frames():
    tracker = TemporalSmoothingTracker(required_consecutive_frames=4)
    cam = "CAM-TEST"

    # Frame 1
    conf, just_trans, count = tracker.process_frame_detection(cam, detected=True, confidence=0.8)
    assert conf is False
    assert just_trans is False
    assert count == 1

    # Frame 2
    conf, just_trans, count = tracker.process_frame_detection(cam, detected=True, confidence=0.85)
    assert conf is False
    assert just_trans is False
    assert count == 2

    # Frame 3
    conf, just_trans, count = tracker.process_frame_detection(cam, detected=True, confidence=0.88)
    assert conf is False
    assert just_trans is False
    assert count == 3

    # Frame 4 -> Threshold reached!
    conf, just_trans, count = tracker.process_frame_detection(cam, detected=True, confidence=0.90)
    assert conf is True
    assert just_trans is True  # Exactly on the 4th frame
    assert count == 4

    # Frame 5 -> Still confirmed, but just_trans should be False (no duplicate event)
    conf, just_trans, count = tracker.process_frame_detection(cam, detected=True, confidence=0.91)
    assert conf is True
    assert just_trans is False
    assert count == 5


def test_temporal_smoothing_resets_on_lost_track():
    tracker = TemporalSmoothingTracker(required_consecutive_frames=4)
    cam = "CAM-LOST"

    # 3 consecutive detections
    for _ in range(3):
        tracker.process_frame_detection(cam, detected=True)

    # Miss multiple frames
    for _ in range(4):
        conf, _, count = tracker.process_frame_detection(cam, detected=False)

    assert conf is False
    assert count == 0


def test_beacon_heuristic_on_synthetic_ambulance():
    heuristic = BeaconColorHeuristic(HeuristicConfig())

    # Create synthetic image with white chassis, red stripe, and blue strobe
    crop = np.full((100, 80, 3), (245, 245, 245), dtype=np.uint8)  # White body
    # Red stripe in middle
    crop[45:55, :, :] = (0, 0, 230)
    # Red & blue beacon circles on top
    crop[10:20, 20:30, :] = (0, 0, 255)    # Red strobe
    crop[10:20, 50:60, :] = (255, 100, 0)  # Blue strobe

    is_emergency, confidence, metrics = heuristic.analyze_vehicle(crop)
    assert is_emergency is True
    assert confidence >= 0.48
    assert metrics["white_ratio"] > 0.2


def test_beacon_heuristic_on_regular_car():
    heuristic = BeaconColorHeuristic(HeuristicConfig())

    # Plain dark vehicle crop
    crop = np.full((100, 80, 3), (40, 40, 40), dtype=np.uint8)
    is_emergency, confidence, metrics = heuristic.analyze_vehicle(crop)
    assert is_emergency is False
    assert confidence < 0.3
