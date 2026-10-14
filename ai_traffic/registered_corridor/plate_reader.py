"""OpenCV plate localization and Tesseract OCR for configured road cameras."""

from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np


@dataclass
class PlateRead:
    text: str
    confidence: float
    box: tuple[int, int, int, int]


class PlateReader:
    """Find plate-shaped regions, OCR them, then let the registry verify exact IDs."""

    def __init__(self, min_confidence: float = 55.0):
        self.min_confidence = min_confidence
        self._ocr = None
        self.error: Optional[str] = None
        try:
            import pytesseract
            import os
            if os.getenv("TESSERACT_CMD"):
                pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
            # Importing pytesseract alone does not mean its native OCR binary exists.
            pytesseract.get_tesseract_version()
            self._ocr = pytesseract
        except Exception as exc:
            # Keep the dashboard available while clearly reporting why live OCR is off.
            self.error = str(exc)

    @property
    def ready(self) -> bool:
        return self._ocr is not None

    def scan(self, frame: np.ndarray) -> List[PlateRead]:
        if self._ocr is None or frame is None or frame.size == 0:
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        edges = cv2.Canny(gray, 40, 160)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        height, width = gray.shape
        candidates = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            ratio = w / max(h, 1)
            area = w * h
            if 2.0 <= ratio <= 6.5 and width * height * 0.00035 <= area <= width * height * 0.08:
                candidates.append((area, x, y, w, h))
        reads: List[PlateRead] = []
        for _, x, y, w, h in sorted(candidates, reverse=True)[:8]:
            pad_x, pad_y = max(2, int(w * .04)), max(2, int(h * .15))
            x1, y1 = max(0, x - pad_x), max(0, y - pad_y)
            x2, y2 = min(width, x + w + pad_x), min(height, y + h + pad_y)
            crop = gray[y1:y2, x1:x2]
            crop = cv2.resize(crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            crop = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            config = "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            try:
                data = self._ocr.image_to_data(crop, config=config, output_type=self._ocr.Output.DICT)
                self.error = None
            except Exception as exc:
                self.error = str(exc)
                return []
            text = "".join(data["text"]).upper()
            confidences = [float(c) for c in data["conf"] if str(c).strip() not in {"", "-1"}]
            confidence = sum(confidences) / len(confidences) if confidences else 0.0
            if len(text) >= 8 and confidence >= self.min_confidence:
                reads.append(PlateRead(text=text, confidence=confidence, box=(x1, y1, x2, y2)))
        return reads

    @staticmethod
    def annotate(frame: np.ndarray, plate: PlateRead, verified: bool) -> np.ndarray:
        output = frame.copy()
        color = (40, 210, 130) if verified else (40, 170, 255)
        x1, y1, x2, y2 = plate.box
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        cv2.putText(output, f"{plate.text}  {plate.confidence:.0f}%", (x1, max(20, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 2)
        return output
