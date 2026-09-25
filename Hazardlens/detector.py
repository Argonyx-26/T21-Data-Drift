"""
Hazardlens - Detection Pipeline
----------------------------------
Combines two checks on each video frame:
  1. PPE compliance: is a detected head wearing a helmet?
  2. Zone intrusion: is a detected person inside the restricted zone?

Returns structured violation events that the dashboard (app.py) displays.
"""

import time
from dataclasses import dataclass, field
from typing import List

from ultralytics import YOLO

from zone_utils import is_inside_zone, bbox_bottom_center, draw_zone

# Colors (BGR, for OpenCV)
COLOR_SAFE = (0, 200, 0)        # green
COLOR_PPE_VIOLATION = (0, 0, 255)   # red
COLOR_ZONE_VIOLATION = (0, 140, 255)  # orange
COLOR_PERSON = (255, 200, 0)


@dataclass
class Violation:
    type: str          # "PPE" or "ZONE"
    timestamp: float
    confidence: float
    details: str = ""


class SafeZoneDetector:
    def __init__(self, weights_path="best.pt", conf_threshold=0.4):
        """
        weights_path: path to your trained YOLOv8 weights
                      (runs/safezone_ai/weights/best.pt after training)
        conf_threshold: minimum confidence to count a detection
        """
        self.model = YOLO(weights_path)
        self.conf_threshold = conf_threshold
        self.class_names = self.model.names  # e.g. {0:'head',1:'helmet',2:'person'}

    def process_frame(self, frame):
        """
        Runs detection on a single frame.
        Returns: (annotated_frame, list_of_violations_this_frame)
        """
        violations: List[Violation] = []
        results = self.model(frame, conf=self.conf_threshold, verbose=False)[0]

        heads, helmets, persons = [], [], []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            label = self.class_names[cls_id]
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

            if label == "head":
                heads.append((xyxy, conf))
            elif label == "helmet":
                helmets.append((xyxy, conf))
            elif label == "person":
                persons.append((xyxy, conf))

        frame = draw_zone(frame)

        # --- Check 1: PPE compliance (bare head = violation) ---
        for (hx1, hy1, hx2, hy2), conf in heads:
            # If this "head" box doesn't overlap significantly with any
            # helmet box, treat it as a bare-head (non-compliant) worker.
            covered = any(
                self._iou((hx1, hy1, hx2, hy2), helm_box) > 0.2
                for helm_box, _ in helmets
            )
            color = COLOR_SAFE if covered else COLOR_PPE_VIOLATION
            self._draw_box(frame, (hx1, hy1, hx2, hy2), color,
                            "Helmet OK" if covered else "NO HELMET", conf)
            if not covered:
                violations.append(Violation(
                    type="PPE",
                    timestamp=time.time(),
                    confidence=conf,
                    details="Worker without helmet detected",
                ))

        # --- Check 2: Zone intrusion ---
        for box, conf in persons:
            foot_point = bbox_bottom_center(box)
            inside = is_inside_zone(foot_point)
            color = COLOR_ZONE_VIOLATION if inside else COLOR_PERSON
            self._draw_box(frame, box, color,
                            "ZONE INTRUSION" if inside else "Person", conf)
            if inside:
                violations.append(Violation(
                    type="ZONE",
                    timestamp=time.time(),
                    confidence=conf,
                    details="Person entered restricted zone",
                ))

        return frame, violations

    @staticmethod
    def _iou(box1, box2):
        """Intersection-over-union between two (x1,y1,x2,y2) boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0

    @staticmethod
    def _draw_box(frame, box, color, label, conf):
        import cv2
        x1, y1, x2, y2 = [int(v) for v in box]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf:.2f}"
        cv2.putText(frame, text, (x1, max(y1 - 8, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
