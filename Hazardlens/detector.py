"""
HazardLens — Detection Pipeline (Dual-Model Architecture)
----------------------------------------------------------

Architecture:
    1. Custom model  (best.pt)    → head + helmet detection
    2. Pretrained    (yolov8n.pt) → person detection

Core Intrusion Rule:
    - Person inside restricted area WITHOUT PPE (helmet) = INTRUSION (and PPE Violation)
    - Person inside restricted area WITH PPE (helmet)    = NO INTRUSION (Authorized, Safe)
    - Person outside restricted area WITHOUT PPE (helmet) = PPE VIOLATION
    - Person outside restricted area WITH PPE (helmet)    = Normal (Safe)
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
COLOR_INTRUSION      = (0, 0, 255)       # Red    — intrusion / no helmet in zone
COLOR_PERSON_OUTSIDE = (255, 200, 0)     # Cyan   — person outside zone
COLOR_NO_HELMET      = (0, 80, 255)      # Dark orange/red — no helmet

_COOLDOWN_FRAMES = 30   # ~1 second at 30 fps


# ============================================================
# VIOLATION DATA STRUCTURE
# ============================================================

@dataclass
class Violation:
    """One discrete violation event."""
    type: str                    # "INTRUSION" or "PPE"
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
    Only flags an intrusion if a person enters the restricted zone WITHOUT PPE.
    """

    def __init__(
        self,
        ppe_weights: str = "best.pt",
        person_weights: str = "yolov8n.pt",
        conf_threshold: float = 0.4,
        zone_coords: Optional[list] = None,
    ):
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

        # Sensitive threshold for PPE so helmets are not discarded when user increases slider
        ppe_conf_thresh = max(0.20, min(0.35, self.conf_threshold))
        ppe_results = self.ppe_model.track(
            frame,
            conf=ppe_conf_thresh,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
        )[0]

        # Use an adaptive high-recall threshold (0.25) for person detection
        person_conf_thresh = max(0.20, min(0.25, self.conf_threshold))
        person_results = self.person_model.track(
            frame,
            conf=person_conf_thresh,
            classes=[0],
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False,
        )[0]

        # ────────────────────────────────────────────────────────
        # 2. Collect head, helmet, and model-detected persons
        # ────────────────────────────────────────────────────────

        heads = []    # [(coords, conf, track_id), ...]
        helmets = []
        candidate_persons = []  # [(coords, conf, track_id, source), ...]

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
            elif cls_name == "person" and confidence >= person_conf_thresh:
                candidate_persons.append((coords, confidence, track_id, "ppe_model"))

        # Add person detections from pretrained COCO model
        for box in person_results.boxes:
            if int(box.cls[0]) == 0:
                coords = box.xyxy[0].tolist()
                conf   = float(box.conf[0])
                tid    = int(box.id[0]) if box.id is not None else None
                candidate_persons.append((coords, conf, tid, "coco_model"))

        # ────────────────────────────────────────────────────────
        # 3. High-Recall Recovery: Infer Person from Head/Helmet
        # ────────────────────────────────────────────────────────
        all_headwear = heads + helmets
        for h_coords, h_conf, _ in all_headwear:
            hx1, hy1, hx2, hy2 = h_coords
            hc_x = (hx1 + hx2) / 2
            hc_y = (hy1 + hy2) / 2

            has_body = any(
                (p[0][0] <= hc_x <= p[0][2] and p[0][1] <= hc_y <= p[0][3])
                for p in candidate_persons
            )

            if not has_body:
                hw = max(10.0, hx2 - hx1)
                hh = max(10.0, hy2 - hy1)
                px1 = max(0, hc_x - hw * 1.25)
                px2 = min(frame_w, hc_x + hw * 1.25)
                py1 = max(0, hy1 - hh * 0.15)
                py2 = min(frame_h, hy1 + hh * 4.8)
                candidate_persons.append(([px1, py1, px2, py2], h_conf, None, "head_proxy"))

        # NMS deduplication to merge overlapping person candidates
        final_persons = self._nms_boxes(candidate_persons, iou_thresh=0.35)

        # ────────────────────────────────────────────────────────
        # 4. Check persons against Zone and PPE
        # ────────────────────────────────────────────────────────

        intrusion_this_frame = set()
        ppe_this_frame = set()
        active_intrusion = False

        for coords, confidence, track_id, source in final_persons:
            effective_id = track_id
            if effective_id is None:
                cx = int((coords[0] + coords[2]) / 2 / 120)
                cy = int((coords[1] + coords[3]) / 2 / 120)
                effective_id = f"cell_{cx}_{cy}"

            inside_zone = is_person_in_zone(coords, frame_w, frame_h, self.zone_coords)
            has_helmet = self._person_has_helmet(coords, heads, helmets)

            # ── Intrusion & PPE Rule ───────────────────────────
            # Rule: ONLY person in restricted zone WITHOUT PPE = INTRUSION
            # If wearing PPE inside zone = ALLOWED (NO INTRUSION)
            if inside_zone and not has_helmet:
                # 🚨 INTRUSION: Inside restricted area WITHOUT PPE
                active_intrusion = True
                intrusion_this_frame.add(effective_id)
                self._intrusion_clean.pop(effective_id, None)

                if effective_id not in self._intrusion_seen:
                    self._intrusion_seen.add(effective_id)
                    violations.append(
                        Violation(
                            type="INTRUSION",
                            timestamp=time.time(),
                            confidence=confidence,
                            details="Worker entered restricted zone without helmet",
                            track_id=track_id,
                        )
                    )

                color = COLOR_INTRUSION
                label = "🚨 INTRUSION: NO HELMET"

            elif inside_zone and has_helmet:
                # ✓ Person in restricted area WITH PPE = NO INTRUSION (ALLOWED)
                color = COLOR_SAFE
                label = "✓ AUTHORIZED (HELMET OK)"

            elif not inside_zone and not has_helmet:
                # ⚠ Outside restricted area WITHOUT PPE = PPE VIOLATION
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

                color = COLOR_NO_HELMET
                label = "⚠ NO HELMET"

            else:
                # Outside restricted area WITH PPE = NORMAL
                color = COLOR_SAFE
                label = "Person (Helmet OK)"

            self._draw_box(frame, coords, color, label, confidence)

        # ────────────────────────────────────────────────────────
        # 5. Draw restricted-zone overlay (alerts only if unauthorized intrusion)
        # ────────────────────────────────────────────────────────

        frame = draw_zone(frame, zone_norm=self.zone_coords, alert=active_intrusion)

        # ────────────────────────────────────────────────────────
        # 6. Draw head/helmet tags with mutual suppression on same head
        # ────────────────────────────────────────────────────────

        drawn_helmets = set()
        for head_box, conf, _ in heads:
            matching_helmets = [
                (i, hb, hconf) for i, (hb, hconf, _) in enumerate(helmets)
                if self._iou(head_box, hb) > 0.20
            ]
            if matching_helmets:
                best_match = max(matching_helmets, key=lambda x: x[2])
                drawn_helmets.add(best_match[0])
                if best_match[2] > (conf + 0.10):
                    self._draw_box(frame, best_match[1], COLOR_SAFE, "Helmet OK", best_match[2], small=True)
                else:
                    self._draw_box(frame, head_box, COLOR_INTRUSION, "NO HELMET", conf, small=True)
            else:
                self._draw_box(frame, head_box, COLOR_INTRUSION, "NO HELMET", conf, small=True)

        for i, (helmet_box, conf, _) in enumerate(helmets):
            if i not in drawn_helmets:
                self._draw_box(frame, helmet_box, COLOR_SAFE, "Helmet", conf, small=True)

        # ────────────────────────────────────────────────────────
        # 7. Cooldown management for deduplication
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

    def _person_has_helmet(self, person_box, heads, helmets):
        """
        Determine if this person has compliant PPE (certified helmet).
        Disambiguates between baseball caps/hair and hardhats.
        """
        px1, py1, px2, py2 = person_box
        pw = max(1.0, px2 - px1)
        ph = max(1.0, py2 - py1)
        # Expand head region upward by 10% and laterally by 10% (helmets sit atop the head)
        head_region = (px1 - pw * 0.10, py1 - ph * 0.10, px2 + pw * 0.10, py1 + ph * 0.45)

        p_helmets = [
            h for h in helmets
            if self._iou(head_region, h[0]) > 0.05 or
            (px1 <= (h[0][0] + h[0][2]) / 2 <= px2 and py1 <= (h[0][1] + h[0][3]) / 2 <= py1 + ph * 0.45)
        ]

        p_heads = [
            h for h in heads
            if self._iou(head_region, h[0]) > 0.05 or
            (px1 <= (h[0][0] + h[0][2]) / 2 <= px2 and py1 <= (h[0][1] + h[0][3]) / 2 <= py1 + ph * 0.45)
        ]

        if not p_helmets and not p_heads:
            return False

        if p_heads and not p_helmets:
            return False

        if p_helmets and not p_heads:
            return True

        # When model predicts both on the same person (e.g. baseball cap):
        # Declare compliant ONLY if helmet confidence significantly exceeds head confidence
        max_helm_conf = max(h[1] for h in p_helmets)
        max_head_conf = max(h[1] for h in p_heads)
        return max_helm_conf > (max_head_conf + 0.10)

    @classmethod
    def _nms_boxes(cls, candidates, iou_thresh=0.35):
        """
        Non-maximum suppression to merge overlapping person candidate boxes.
        Prioritizes direct model detections over synthetic head proxies.
        """
        if not candidates:
            return []

        def sort_key(c):
            type_weight = 1.0 if c[3] != "head_proxy" else 0.5
            return (type_weight, c[1])

        candidates = sorted(candidates, key=sort_key, reverse=True)
        keep = []
        for cand in candidates:
            box = cand[0]
            if not any(cls._iou(box, k[0]) > iou_thresh for k in keep):
                keep.append(cand)
        return keep

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