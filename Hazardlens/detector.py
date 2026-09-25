"""
HazardLens — Detection Pipeline (Dual-Model Architecture)
----------------------------------------------------------

Architecture:
    1. Custom model  (best.pt)    → head + helmet detection
    2. Pretrained    (yolov8n.pt) → person detection

Intrusion logic:
    Person inside the site WITHOUT a helmet = INTRUSION
    Person inside the site WITH a helmet    = ALLOWED (no violation)

    This combines zone monitoring with PPE compliance into a single
    unified "intrusion detection" concept.

Why two models:
    The custom model was trained on the "Hard Hat Workers v10" dataset which
    has severe class imbalance (person class has only 2.3% of annotations).
    The pretrained YOLOv8n provides reliable person detection.

Violation counting:
    Violations are counted as EVENTS, not once per video frame.
    A worker without a helmet for 200 frames = 1 intrusion event.
    This is achieved using ByteTrack tracking + cooldown deduplication.
"""

import time
from dataclasses import dataclass
from typing import List

import cv2
from ultralytics import YOLO

from zone_utils import (
    is_inside_zone,
    bbox_bottom_center,
    draw_zone,
)


# ============================================================
# COLORS — BGR format for OpenCV
# ============================================================

COLOR_SAFE           = (0, 200, 0)       # Green  — helmet present, allowed
COLOR_INTRUSION      = (0, 0, 255)       # Red    — intrusion (no helmet in zone)
COLOR_PERSON_OUTSIDE = (255, 200, 0)     # Cyan   — person outside zone
COLOR_NO_HELMET      = (0, 80, 255)      # Dark orange — no helmet outside zone

# Cooldown period: number of consecutive "clean" frames required
# before a track can trigger a new event.  Prevents rapid toggling
# from inflating the violation count.
_COOLDOWN_FRAMES = 30   # ~1 second at 30 fps


# ============================================================
# VIOLATION DATA STRUCTURE
# ============================================================

@dataclass
class Violation:
    """One discrete violation event (not per-frame)."""
    type: str                    # "INTRUSION"
    timestamp: float             # Unix timestamp when first detected
    confidence: float            # Detection confidence at event start
    details: str = ""
    track_id: int | None = None


# ============================================================
# DETECTOR
# ============================================================

class SafeZoneDetector:
    """
    Dual-model detector for workplace safety monitoring.

    Intrusion = person inside the site WITHOUT proper PPE (helmet).
    Person with helmet = allowed, no violation.
    """

    def __init__(
        self,
        ppe_weights: str = "best.pt",
        person_weights: str = "yolov8n.pt",
        conf_threshold: float = 0.4,
    ):
        """
        Parameters
        ----------
        ppe_weights : str
            Path to the custom YOLO model trained on head/helmet.
        person_weights : str
            Path to a pretrained YOLO model for person detection.
        conf_threshold : float
            Minimum detection confidence (applied to both models).
        """

        # ── Custom model: head + helmet ────────────────────────
        self.ppe_model = YOLO(ppe_weights)
        self.ppe_class_names = self.ppe_model.names

        # ── Pretrained model: person ───────────────────────────
        self.person_model = YOLO(person_weights)

        self.conf_threshold = conf_threshold

        # ── Event deduplication with cooldown ──────────────────
        self._intrusion_seen: set  = set()
        self._intrusion_clean: dict = {}

    # ============================================================
    # PROCESS FRAME
    # ============================================================

    def process_frame(self, frame):
        """
        Analyse one video frame.

        Returns
        -------
        annotated_frame : ndarray
            The frame with bounding boxes and zone overlay drawn.
        violations : list[Violation]
            Only NEW intrusion events detected in this frame.
        """

        violations: List[Violation] = []

        # ────────────────────────────────────────────────────────
        # Run BOTH models on the clean frame (before overlays)
        # ────────────────────────────────────────────────────────

        # PPE model — heads and helmets
        ppe_results = self.ppe_model.track(
            frame,
            conf=self.conf_threshold,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
        )[0]

        # Person model — only COCO class 0 ("person")
        person_results = self.person_model.track(
            frame,
            conf=self.conf_threshold,
            classes=[0],
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
        )[0]

        # ========================================================
        # FRAME DIMENSIONS (for zone coordinate scaling)
        # ========================================================

        frame_h, frame_w = frame.shape[:2]

        # ========================================================
        # DRAW RESTRICTED-ZONE OVERLAY
        # ========================================================

        frame = draw_zone(frame)

        # ========================================================
        # COLLECT HEAD + HELMET DETECTIONS (from custom model)
        # ========================================================

        heads   = []    # [(coords, confidence, track_id), ...]
        helmets = []

        for box in ppe_results.boxes:
            cls_id     = int(box.cls[0])
            cls_name   = self.ppe_class_names[cls_id]
            confidence = float(box.conf[0])
            coords     = box.xyxy[0].tolist()
            track_id   = int(box.id[0]) if box.id is not None else None

            if cls_name == "head":
                heads.append((coords, confidence, track_id))
            elif cls_name == "helmet":
                helmets.append((coords, confidence, track_id))

        # ========================================================
        # COMBINED INTRUSION DETECTION
        # ========================================================
        #
        # For each detected person:
        #   1. Check if they are inside the restricted zone
        #   2. Check if they have a helmet (by checking overlap
        #      between person bbox and helmet/head detections)
        #   3. Person in zone WITHOUT helmet = INTRUSION
        #   4. Person in zone WITH helmet    = ALLOWED (safe)
        #   5. Person outside zone           = just annotated
        #

        intrusion_this_frame: set = set()

        for box in person_results.boxes:

            cls_id = int(box.cls[0])
            if cls_id != 0:
                continue

            confidence = float(box.conf[0])
            coords     = box.xyxy[0].tolist()
            track_id   = int(box.id[0]) if box.id is not None else None

            # ── Check if person is inside restricted zone ──────
            foot_point  = bbox_bottom_center(coords)
            inside_zone = is_inside_zone(foot_point, frame_w, frame_h)

            # ── Check if person has a helmet ───────────────────
            has_helmet = self._person_has_helmet(coords, helmets)

            # ── Determine status ───────────────────────────────

            if inside_zone and not has_helmet:
                # ⚠ INTRUSION: in the zone without PPE
                color = COLOR_INTRUSION
                label = "INTRUSION"

                if track_id is not None:
                    intrusion_this_frame.add(track_id)
                    self._intrusion_clean.pop(track_id, None)

                    if track_id not in self._intrusion_seen:
                        self._intrusion_seen.add(track_id)
                        violations.append(
                            Violation(
                                type="INTRUSION",
                                timestamp=time.time(),
                                confidence=confidence,
                                details="Person in site without helmet",
                                track_id=track_id,
                            )
                        )

            elif inside_zone and has_helmet:
                # ✓ In zone WITH helmet — allowed
                color = COLOR_SAFE
                label = "SAFE"

            elif not inside_zone and not has_helmet:
                # Outside zone without helmet — flag but not intrusion
                color = COLOR_NO_HELMET
                label = "NO HELMET"

            else:
                # Outside zone with helmet — normal
                color = COLOR_PERSON_OUTSIDE
                label = "Person"

            self._draw_box(frame, coords, color, label, confidence)

        # ── Draw head/helmet boxes for visual reference ────────

        for head_box, conf, _ in heads:
            helmet_on = any(
                self._iou(head_box, hb) > 0.2
                for hb, _, _ in helmets
            )
            if helmet_on:
                self._draw_box(frame, head_box, COLOR_SAFE,
                               "Helmet OK", conf)
            else:
                self._draw_box(frame, head_box, COLOR_INTRUSION,
                               "NO HELMET", conf)

        # ── Cooldown: expire old intrusion tracks ──────────────

        for tid in list(self._intrusion_seen):
            if tid not in intrusion_this_frame:
                count = self._intrusion_clean.get(tid, 0) + 1
                if count >= _COOLDOWN_FRAMES:
                    self._intrusion_seen.discard(tid)
                    self._intrusion_clean.pop(tid, None)
                else:
                    self._intrusion_clean[tid] = count

        return frame, violations

    # ============================================================
    # HELMET CHECK FOR A PERSON
    # ============================================================

    def _person_has_helmet(self, person_box, helmets):
        """
        Determine whether a detected person has a helmet.

        Checks if any HELMET bounding box overlaps with the person's
        upper body area (head region).

        Returns True if a helmet is detected on this person.
        """
        px1, py1, px2, py2 = person_box
        person_h = py2 - py1

        if person_h <= 0:
            return False

        # Upper portion of person box (top 35% = head area)
        head_region = (px1, py1, px2, py1 + person_h * 0.35)

        # Check if any helmet overlaps with this person's head region
        for helmet_box, _, _ in helmets:
            if self._iou(head_region, helmet_box) > 0.02:
                return True
            # Also check overlap with full person box (in case
            # helmet bbox is small relative to person bbox)
            if self._box_contains(person_box, helmet_box):
                return True

        return False

    # ============================================================
    # BOX CONTAINS CHECK
    # ============================================================

    @staticmethod
    def _box_contains(outer, inner):
        """Check if the center of inner box is within outer box."""
        ix_center = (inner[0] + inner[2]) / 2
        iy_center = (inner[1] + inner[3]) / 2
        return (outer[0] <= ix_center <= outer[2] and
                outer[1] <= iy_center <= outer[3])

    # ============================================================
    # IOU CALCULATION
    # ============================================================

    @staticmethod
    def _iou(box1, box2):
        """
        Intersection-over-Union between two bounding boxes.
        Each box is (x1, y1, x2, y2).
        """
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)

        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        if union <= 0:
            return 0.0

        return intersection / union

    # ============================================================
    # DRAW BOUNDING BOX
    # ============================================================

    @staticmethod
    def _draw_box(frame, box, color, label, confidence):
        """Draw a labelled bounding box on *frame*."""
        x1, y1, x2, y2 = [int(v) for v in box]

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        text = f"{label} {confidence:.2f}"

        (tw, th), _ = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
        )
        label_y = max(y1, th + 10)
        cv2.rectangle(
            frame,
            (x1, label_y - th - 6),
            (x1 + tw + 6, label_y + 2),
            color, -1,
        )
        cv2.putText(
            frame, text, (x1 + 3, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            (255, 255, 255), 2,
        )