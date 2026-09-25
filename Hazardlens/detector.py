"""
HazardLens — Detection Pipeline (Dual-Model Architecture)
----------------------------------------------------------

Architecture:
    1. Custom model  (best.pt)    → head + helmet detection
    2. Pretrained    (yolov8n.pt) → person detection

Intrusion logic:
    - Person inside the site WITHOUT a helmet = INTRUSION (Critical safety hazard)
    - Person inside the site WITH a helmet    = AUTHORIZED / SAFE
    - Person outside the site WITHOUT a helmet = PPE VIOLATION

Violation counting:
    Violations are counted as distinct EVENTS using ByteTrack tracking + cooldown.
    A worker in the site for 200 frames triggers 1 intrusion event, not 200.
"""

import time
from dataclasses import dataclass
from typing import List, Optional

import cv2
from ultralytics import YOLO

from zone_utils import (
    RESTRICTED_ZONE,
    is_person_in_zone,
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

_COOLDOWN_FRAMES = 30   # ~1 second at 30 fps


# ============================================================
# VIOLATION DATA STRUCTURE
# ============================================================

@dataclass
class Violation:
    """One discrete violation event."""
    type: str                    # "INTRUSION", "PPE", or "ZONE"
    timestamp: float             # Unix timestamp when first detected
    confidence: float            # Detection confidence at event start
    details: str = ""
    track_id: Optional[int] = None


# ============================================================
# DETECTOR
# ============================================================

class SafeZoneDetector:
    """
    Dual-model detector for workplace safety monitoring.

    Combines person detection with head/helmet PPE classification.
    Person inside site without helmet = INTRUSION.
    """

    def __init__(
        self,
        ppe_weights: str = "best.pt",
        person_weights: str = "yolov8n.pt",
        conf_threshold: float = 0.4,
        zone_coords: Optional[list] = None,
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
        zone_coords : list of (float, float), optional
            Normalized restricted zone polygon vertices.
        """
        # ── Custom model: head + helmet ────────────────────────
        self.ppe_model = YOLO(ppe_weights)
        self.ppe_class_names = self.ppe_model.names

        # ── Pretrained model: person ───────────────────────────
        self.person_model = YOLO(person_weights)

        self.conf_threshold = conf_threshold
        self.zone_coords = zone_coords if zone_coords is not None else RESTRICTED_ZONE

        # ── Event deduplication with cooldown ──────────────────
        self._intrusion_seen: set = set()
        self._intrusion_clean: dict = {}

        self._ppe_seen: set = set()
        self._ppe_clean: dict = {}

    def set_zone(self, zone_coords: list):
        """Update the restricted zone coordinates."""
        self.zone_coords = zone_coords

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
            Only NEW violation events detected in this frame.
        """
        violations: List[Violation] = []
        frame_h, frame_w = frame.shape[:2]

        # ────────────────────────────────────────────────────────
        # 1. Run BOTH models on the clean frame
        # ────────────────────────────────────────────────────────

        ppe_results = self.ppe_model.track(
            frame,
            conf=self.conf_threshold,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
        )[0]

        person_results = self.person_model.track(
            frame,
            conf=self.conf_threshold,
            classes=[0],
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
        )[0]

        # ────────────────────────────────────────────────────────
        # 2. Collect head and helmet detections
        # ────────────────────────────────────────────────────────

        heads = []    # [(coords, conf, track_id), ...]
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

        # ────────────────────────────────────────────────────────
        # 3. Check persons against Zone and PPE
        # ────────────────────────────────────────────────────────

        intrusion_this_frame = set()
        ppe_this_frame = set()
        active_intrusion = False

        # Sort persons by area (larger = closer, process first)
        person_boxes = sorted(
            person_results.boxes,
            key=lambda b: (b.xyxy[0][2] - b.xyxy[0][0]) * (b.xyxy[0][3] - b.xyxy[0][1]),
            reverse=True,
        )

        for box in person_boxes:
            cls_id = int(box.cls[0])
            if cls_id != 0:
                continue

            confidence = float(box.conf[0])
            coords     = box.xyxy[0].tolist()
            track_id   = int(box.id[0]) if box.id is not None else None

            # Fallback tracking ID based on spatial cell if tracker drops id
            effective_id = track_id
            if effective_id is None:
                cx = int((coords[0] + coords[2]) / 2 / 120)
                cy = int((coords[1] + coords[3]) / 2 / 120)
                effective_id = f"cell_{cx}_{cy}"

            # Zone & PPE checks
            inside_zone = is_person_in_zone(coords, frame_w, frame_h, self.zone_coords)
            has_helmet = self._person_has_helmet(coords, helmets)

            # ── Determine status ───────────────────────────────
            if inside_zone and not has_helmet:
                # ⚠ CRITICAL INTRUSION: inside site without helmet
                active_intrusion = True
                color = COLOR_INTRUSION
                label = "INTRUSION: NO HELMET"

                intrusion_this_frame.add(effective_id)
                self._intrusion_clean.pop(effective_id, None)

                if effective_id not in self._intrusion_seen:
                    self._intrusion_seen.add(effective_id)
                    violations.append(
                        Violation(
                            type="INTRUSION",
                            timestamp=time.time(),
                            confidence=confidence,
                            details="Worker in restricted site without helmet",
                            track_id=track_id,
                        )
                    )

            elif inside_zone and has_helmet:
                # ✓ Inside site WITH helmet — authorized
                color = COLOR_SAFE
                label = "AUTHORIZED (HELMET OK)"

            elif not inside_zone and not has_helmet:
                # Outside site without helmet — PPE violation
                color = COLOR_NO_HELMET
                label = "NO HELMET"

                ppe_this_frame.add(effective_id)
                self._ppe_clean.pop(effective_id, None)

                if effective_id not in self._ppe_seen:
                    self._ppe_seen.add(effective_id)
                    violations.append(
                        Violation(
                            type="PPE",
                            timestamp=time.time(),
                            confidence=confidence,
                            details="Worker without helmet detected",
                            track_id=track_id,
                        )
                    )

            else:
                # Outside site with helmet — normal
                color = COLOR_PERSON_OUTSIDE
                label = "Person"

            self._draw_box(frame, coords, color, label, confidence)

        # ────────────────────────────────────────────────────────
        # 4. Draw restricted-zone overlay (alerts if intrusion)
        # ────────────────────────────────────────────────────────

        frame = draw_zone(frame, zone_norm=self.zone_coords, alert=active_intrusion)

        # ────────────────────────────────────────────────────────
        # 5. Draw head and helmet bounding boxes for clarity
        # ────────────────────────────────────────────────────────

        for head_box, conf, _ in heads:
            helmet_on = any(self._iou(head_box, hb) > 0.15 for hb, _, _ in helmets)
            if helmet_on:
                self._draw_box(frame, head_box, COLOR_SAFE, "Helmet OK", conf, small=True)
            else:
                self._draw_box(frame, head_box, COLOR_INTRUSION, "NO HELMET", conf, small=True)

        for helmet_box, conf, _ in helmets:
            self._draw_box(frame, helmet_box, COLOR_SAFE, "Helmet", conf, small=True)

        # ────────────────────────────────────────────────────────
        # 6. Cooldown management for deduplication
        # ────────────────────────────────────────────────────────

        for tid in list(self._intrusion_seen):
            if tid not in intrusion_this_frame:
                count = self._intrusion_clean.get(tid, 0) + 1
                if count >= _COOLDOWN_FRAMES:
                    self._intrusion_seen.discard(tid)
                    self._intrusion_clean.pop(tid, None)
                else:
                    self._intrusion_clean[tid] = count

        for tid in list(self._ppe_seen):
            if tid not in ppe_this_frame:
                count = self._ppe_clean.get(tid, 0) + 1
                if count >= _COOLDOWN_FRAMES:
                    self._ppe_seen.discard(tid)
                    self._ppe_clean.pop(tid, None)
                else:
                    self._ppe_clean[tid] = count

        return frame, violations

    # ============================================================
    # HELMET OVERLAP CHECK
    # ============================================================

    def _person_has_helmet(self, person_box, helmets):
        """
        Check if any detected helmet corresponds to this person.
        Checks both upper 40% head-zone and overall containment.
        """
        px1, py1, px2, py2 = person_box
        person_h = max(1.0, py2 - py1)

        head_region = (px1, py1, px2, py1 + person_h * 0.40)

        for helmet_box, _, _ in helmets:
            # Direct IOU with upper body region
            if self._iou(head_region, helmet_box) > 0.02:
                return True
            # Center of helmet is in upper half of person box
            hx_c = (helmet_box[0] + helmet_box[2]) / 2
            hy_c = (helmet_box[1] + helmet_box[3]) / 2
            if px1 <= hx_c <= px2 and py1 <= hy_c <= (py1 + person_h * 0.50):
                return True
            # Full person box contains helmet center
            if self._box_contains(person_box, helmet_box):
                return True

        return False

    @staticmethod
    def _box_contains(outer, inner):
        """Check if inner center is within outer box."""
        ix_center = (inner[0] + inner[2]) / 2
        iy_center = (inner[1] + inner[3]) / 2
        return (outer[0] <= ix_center <= outer[2] and
                outer[1] <= iy_center <= outer[3])

    @staticmethod
    def _iou(box1, box2):
        """Intersection-over-Union."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
        area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
        union = area1 + area2 - intersection

        return (intersection / union) if union > 0 else 0.0

    @staticmethod
    def _draw_box(frame, box, color, label, confidence, small=False):
        """Draw a stylish bounding box with filled header tag."""
        x1, y1, x2, y2 = [int(v) for v in box]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2 if small else 3)

        text = f"{label} {confidence:.2f}"
        font_scale = 0.45 if small else 0.60
        font_thick = 1 if small else 2

        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thick)
        label_y = max(y1, th + 8)

        # Background tag
        cv2.rectangle(
            frame,
            (x1, label_y - th - 5),
            (x1 + tw + 6, label_y + 4),
            color,
            -1,
        )
        # White text inside colored tag
        cv2.putText(
            frame,
            text,
            (x1 + 3, label_y - 1),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            font_thick,
        )