"""
generate_plate_image.py
Run once to write a tiny JPEG containing a fake plate text into this folder.
Usage: python sample_data/generate_plate_image.py
Requires: opencv-python (already in requirements.txt)
"""

import cv2
import numpy as np
import pathlib

# Plate text that is registered in ambulance_registry.json
PLATE_TEXT = "KA01AB1234"

# Create a white plate-sized image
img = np.ones((100, 300, 3), dtype=np.uint8) * 255

# Draw a black border
cv2.rectangle(img, (5, 5), (295, 95), (0, 0, 0), 3)

# Write the plate text in bold black
cv2.putText(img, PLATE_TEXT, (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 0), 4, cv2.LINE_AA)

out_path = pathlib.Path(__file__).parent / "plate_test.jpg"
cv2.imwrite(str(out_path), img)
print(f"[OK] Plate test image saved to {out_path}")
