"""
Temporal Smoothing Filter and Detection Tracker.
Maintains consecutive detection history across video frames to prevent transient false triggers.
Only emits a confirmed emergency alert once N consecutive frames observe an ambulance.
"""

from typing import Dict, List, Optional, Tuple


def calculate_iou(boxA: List[int], boxB: List[int]) -> float:
    """
    Computes Intersection-over-Union between two bounding boxes [x1, y1, x2, y2].
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    return float(interArea) / float(boxAArea + boxBArea - interArea)


class CameraTrackState:
    def __init__(self, required_consecutive_frames: int = 4):
        self.required_frames = required_consecutive_frames
        self.consecutive_count = 0
        self.is_confirmed = False
        self.last_bbox: Optional[List[int]] = None
        self.last_confidence: float = 0.0
        self.frames_without_detection = 0
        self.max_grace_frames = 2  # Allow up to 2 dropped frames without immediately resetting

    def update(self, detected: bool, bbox: Optional[List[int]] = None, confidence: float = 0.0) -> Tuple[bool, bool]:
        """
        Updates tracking state with frame detection result.

        Returns:
            Tuple (is_confirmed: bool, just_transitioned: bool)
            - is_confirmed: whether state is currently confirmed
            - just_transitioned: True only on the exact frame when confirmation threshold is reached
        """
        just_transitioned = False

        if detected:
            self.frames_without_detection = 0
            self.last_bbox = bbox
            self.last_confidence = confidence
            self.consecutive_count += 1

            if self.consecutive_count >= self.required_frames:
                if not self.is_confirmed:
                    self.is_confirmed = True
                    just_transitioned = True
        else:
            self.frames_without_detection += 1
            if self.frames_without_detection > self.max_grace_frames:
                self.consecutive_count = 0
                self.is_confirmed = False
                self.last_bbox = None
                self.last_confidence = 0.0

        return self.is_confirmed, just_transitioned

    def reset(self) -> None:
        self.consecutive_count = 0
        self.is_confirmed = False
        self.last_bbox = None
        self.last_confidence = 0.0
        self.frames_without_detection = 0


class TemporalSmoothingTracker:
    """
    Tracks emergency vehicle presence across all camera feeds.
    """

    def __init__(self, required_consecutive_frames: int = 4):
        self.required_frames = required_consecutive_frames
        self._states: Dict[str, CameraTrackState] = {}

    def get_or_create_state(self, camera_id: str) -> CameraTrackState:
        if camera_id not in self._states:
            self._states[camera_id] = CameraTrackState(self.required_frames)
        return self._states[camera_id]

    def process_frame_detection(
        self,
        camera_id: str,
        detected: bool,
        bbox: Optional[List[int]] = None,
        confidence: float = 0.0
    ) -> Tuple[bool, bool, int]:
        """
        Returns (is_confirmed, just_transitioned, consecutive_count)
        """
        state = self.get_or_create_state(camera_id)
        is_confirmed, just_transitioned = state.update(detected, bbox, confidence)
        return is_confirmed, just_transitioned, state.consecutive_count

    def reset_camera(self, camera_id: str) -> None:
        if camera_id in self._states:
            self._states[camera_id].reset()
