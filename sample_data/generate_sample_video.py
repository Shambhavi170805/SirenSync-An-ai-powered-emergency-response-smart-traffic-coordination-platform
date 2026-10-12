"""
Sample Video Generator for SirenSync Green Corridor Testing.
Synthesizes an MP4 video (sample_traffic.mp4) depicting junction traffic and a passing
emergency ambulance with flashing beacons.
"""

import os
from pathlib import Path
import cv2
import numpy as np
from ai_traffic.camera.synthetic_feed import SyntheticTrafficFeed


def generate_video(output_path: str = "sample_data/sample_traffic.mp4", num_frames: int = 300, fps: int = 25):
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    feed = SyntheticTrafficFeed(camera_id="CAM-OFFLINE-TEST", junction_id="J-101", fps=fps)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (640, 480))

    print(f"Generating {num_frames} frames to {out_file}...")
    for i in range(num_frames):
        if i == 50:
            feed.trigger_ambulance()
        ret, frame = feed.read()
        if ret and frame is not None:
            writer.write(frame)

    writer.release()
    print(f"Sample video created successfully at: {out_file.resolve()}")


if __name__ == "__main__":
    generate_video()
