"""
HazardLens — Detection Pipeline (Decoupled Dual-Model Architecture)
-------------------------------------------------------------------

Architecture:
    1. Custom model  (best.pt)    → head + helmet + person detection
    2. Pretrained    (yolov8n.pt) → complementary person detection

Core Intrusion Rule:
    - Person inside restricted area WITHOUT PPE (helmet) = INTRUSION (and PPE Violation)
    - Person inside restricted area WITH PPE (helmet)    = NO INTRUSION (Authorized, Safe)
    - Person outside restricted area WITHOUT PPE (helmet) = PPE VIOLATION
    - Person outside restricted area WITH PPE (helmet)    = Normal (Safe)

Decoupled Performance Architecture:
    • Asynchronous background AI worker running on independent thread
    • Continuous ~40 FPS video display loop with zero YOLO blocking
    • Thread-safe latest-frame buffer (drops stale frames, zero queue lag)
    • Normalized coordinate detection buffer for resolution-independent <0.5ms rendering
    • Persistent model caching via @st.cache_resource
    • Automatic CUDA / CPU selection with FP16 where supported
    • Real-time ByteTrack tracking & violation deduplication
"""

import time
import os
import threading
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

import cv2
import torch
import streamlit as st
from ultralytics import YOLO

from zone_utils import (
    RESTRICTED_ZONE,
    is_person_in_zone,
    draw_zone,
)

# Enable OpenCV & PyTorch execution optimizations
cv2.setUseOptimized(True)
torch.set_grad_enabled(False)
if hasattr(torch, "set_num_threads"):
    try:
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 4)))
    except Exception:
        pass


# ============================================================
# COLORS — BGR format for OpenCV
# ============================================================

COLOR_SAFE           = (0, 200, 0)       # Green  — helmet present, allowed
COLOR_INTRUSION      = (0, 0, 255)       # Red    — intrusion / no helmet in zone
COLOR_PERSON_OUTSIDE = (255, 200, 0)     # Cyan   — person outside zone
COLOR_NO_HELMET      = (0, 80, 255)      # Dark orange/red — no helmet

_COOLDOWN_FRAMES = 15   # Detection cycles cooldown for deduplication


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
# MODEL CACHING & HARDWARE SELECTION
# ============================================================

def get_optimal_device() -> str:
    """Detect CUDA GPU or CPU."""
    if torch.cuda.is_available():
        return "0"
    return "cpu"


@st.cache_resource(show_spinner=False)
def load_cached_yolo_models(
    ppe_weights: str = "best.pt",
    person_weights: str = "yolov8n.pt",
    device: str = "cpu"
) -> Tuple[YOLO, YOLO]:
    """
    Load YOLO models ONCE into memory.
    Cached persistently by Streamlit to eliminate re-initialization overhead.
    """
    ppe_model = YOLO(ppe_weights)
    person_model = YOLO(person_weights)
    if device != "cpu":
        try:
            ppe_model.to(device)
            person_model.to(device)
        except Exception:
            pass
    return ppe_model, person_model


# ============================================================
# DETECTOR
# ============================================================

class SafeZoneDetector:
    """
    Dual-model detector for workplace safety monitoring.
    Only flags an intrusion if a person enters the restricted zone WITHOUT PPE.
    Produces normalized coordinates for resolution-independent <0.5ms annotation.
    """

    def __init__(
        self,
        ppe_weights: str = "best.pt",
        person_weights: str = "yolov8n.pt",
        conf_threshold: float = 0.4,
        zone_coords: Optional[list] = None,
        ppe_model: Optional[YOLO] = None,
        person_model: Optional[YOLO] = None,
        imgsz: int = 320,
        device: Optional[str] = None,
    ):
        self.device = device if device is not None else get_optimal_device()
        self.imgsz = imgsz
        self.is_cuda = (self.device != "cpu" and torch.cuda.is_available())

        # ── Reuse cached models ────────────────────────────────
        if ppe_model is not None and person_model is not None:
            self.ppe_model = ppe_model
            self.person_model = person_model
        else:
            self.ppe_model, self.person_model = load_cached_yolo_models(
                ppe_weights, person_weights, self.device
            )

        self.ppe_class_names = self.ppe_model.names
        self.conf_threshold = conf_threshold
        self.zone_coords = zone_coords if zone_coords is not None else RESTRICTED_ZONE

        # ── Event deduplication with cooldown ──────────────────
        self._intrusion_seen: set = set()
        self._intrusion_clean: dict = {}

        self._ppe_seen: set = set()
        self._ppe_clean: dict = {}

        # ── Cached state for fast annotation ───────────────────
        self._cached_boxes_to_draw: list = []
        self._cached_heads_to_draw: list = []
        self._cached_helmets_to_draw: list = []
        self._cached_active_intrusion: bool = False
        self._inference_step: int = 0

    def set_zone(self, zone_coords: list):
        """Update the restricted zone coordinates."""
        self.zone_coords = zone_coords

    # ============================================================
    # ANALYZE FRAME (Heavy AI pipeline executed in background)
    # ============================================================

    def analyze_frame(self, frame) -> Tuple[dict, List[Violation]]:
        """
        Run full dual-model YOLO inference, ByteTrack, zone geometry & PPE logic.
        Returns:
            ai_data : dict of normalized visual bounding boxes and alert status
            violations : list of newly triggered Violation events
        """
        violations: List[Violation] = []
        frame_h, frame_w = frame.shape[:2]
        inv_w = 1.0 / max(1, frame_w)
        inv_h = 1.0 / max(1, frame_h)
        self._inference_step += 1

        with torch.inference_mode():
            # 1. Primary Model: best.pt (head, helmet, person)
            ppe_conf_thresh = max(0.20, min(0.35, self.conf_threshold))
            ppe_results = self.ppe_model.track(
                frame,
                conf=ppe_conf_thresh,
                imgsz=self.imgsz,
                device=self.device,
                persist=True,
                tracker="bytetrack.yaml",
                verbose=False,
                half=self.is_cuda,
            )[0]

            heads = []
            helmets = []
            candidate_persons = []

            if ppe_results.boxes is not None and len(ppe_results.boxes) > 0:
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
                    elif cls_name == "person" and confidence >= 0.20:
                        candidate_persons.append((coords, confidence, track_id, "ppe_model"))

            # 2. Complementary Model: yolov8n.pt (person detection)
            should_run_coco_person = (len(candidate_persons) == 0) or (self._inference_step % 2 == 0)
            if should_run_coco_person:
                person_conf_thresh = max(0.20, min(0.25, self.conf_threshold))
                person_results = self.person_model.track(
                    frame,
                    conf=person_conf_thresh,
                    classes=[0],
                    imgsz=self.imgsz,
                    device=self.device,
                    persist=True,
                    tracker="bytetrack.yaml",
                    verbose=False,
                    half=self.is_cuda,
                )[0]

                if person_results.boxes is not None and len(person_results.boxes) > 0:
                    for box in person_results.boxes:
                        if int(box.cls[0]) == 0:
                            coords = box.xyxy[0].tolist()
                            conf   = float(box.conf[0])
                            tid    = int(box.id[0]) if box.id is not None else None
                            candidate_persons.append((coords, conf, tid, "coco_model"))

            # 3. High-Recall Person Recovery from Head/Helmet
            all_headwear = heads + helmets
            for h_coords, h_conf, _ in all_headwear:
                hx1, hy1, hx2, hy2 = h_coords
                hc_x = (hx1 + hx2) * 0.5
                hc_y = (hy1 + hy2) * 0.5

                has_body = any(
                    (p[0][0] <= hc_x <= p[0][2] and p[0][1] <= hc_y <= p[0][3])
                    for p in candidate_persons
                )

                if not has_body:
                    hw = max(10.0, hx2 - hx1)
                    hh = max(10.0, hy2 - hy1)
                    px1 = max(0.0, hc_x - hw * 1.25)
                    px2 = min(float(frame_w), hc_x + hw * 1.25)
                    py1 = max(0.0, hy1 - hh * 0.15)
                    py2 = min(float(frame_h), hy1 + hh * 4.8)
                    candidate_persons.append(([px1, py1, px2, py2], h_conf, None, "head_proxy"))

            final_persons = self._nms_boxes(candidate_persons, iou_thresh=0.35)

            # 4. Check Zone & PPE Rules
            intrusion_this_frame = set()
            ppe_this_frame = set()
            active_intrusion = False
            boxes_to_draw = []

            for coords, confidence, track_id, source in final_persons:
                effective_id = track_id
                if effective_id is None:
                    cx = int((coords[0] + coords[2]) * 0.5 / 120)
                    cy = int((coords[1] + coords[3]) * 0.5 / 120)
                    effective_id = f"cell_{cx}_{cy}"

                inside_zone = is_person_in_zone(coords, frame_w, frame_h, self.zone_coords)
                has_helmet = self._person_has_helmet(coords, heads, helmets)

                if inside_zone and not has_helmet:
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
                    color = COLOR_SAFE
                    label = "✓ AUTHORIZED (HELMET OK)"

                elif not inside_zone and not has_helmet:
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
                    color = COLOR_SAFE
                    label = "Person (Helmet OK)"

                # Store normalized coordinates: (norm_box, color, label, confidence, small)
                norm_box = [coords[0] * inv_w, coords[1] * inv_h, coords[2] * inv_w, coords[3] * inv_h]
                boxes_to_draw.append((norm_box, color, label, confidence, False))

            heads_to_draw = []
            helmets_to_draw = []
            drawn_helmets = set()

            for head_box, conf, _ in heads:
                matching_helmets = [
                    (i, hb, hconf) for i, (hb, hconf, _) in enumerate(helmets)
                    if self._iou(head_box, hb) > 0.20
                ]
                norm_h = [head_box[0] * inv_w, head_box[1] * inv_h, head_box[2] * inv_w, head_box[3] * inv_h]
                if matching_helmets:
                    best_match = max(matching_helmets, key=lambda x: x[2])
                    drawn_helmets.add(best_match[0])
                    if best_match[2] > (conf + 0.10):
                        nb = [best_match[1][0] * inv_w, best_match[1][1] * inv_h, best_match[1][2] * inv_w, best_match[1][3] * inv_h]
                        helmets_to_draw.append((nb, COLOR_SAFE, "Helmet OK", best_match[2], True))
                    else:
                        heads_to_draw.append((norm_h, COLOR_INTRUSION, "NO HELMET", conf, True))
                else:
                    heads_to_draw.append((norm_h, COLOR_INTRUSION, "NO HELMET", conf, True))

            for i, (helmet_box, conf, _) in enumerate(helmets):
                if i not in drawn_helmets:
                    norm_hb = [helmet_box[0] * inv_w, helmet_box[1] * inv_h, helmet_box[2] * inv_w, helmet_box[3] * inv_h]
                    helmets_to_draw.append((norm_hb, COLOR_SAFE, "Helmet", conf, True))

            # Cooldown management for deduplication
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

            ai_data = {
                "boxes_to_draw": boxes_to_draw,
                "heads_to_draw": heads_to_draw,
                "helmets_to_draw": helmets_to_draw,
                "active_intrusion": active_intrusion,
            }

            self._cached_boxes_to_draw = boxes_to_draw
            self._cached_heads_to_draw = heads_to_draw
            self._cached_helmets_to_draw = helmets_to_draw
            self._cached_active_intrusion = active_intrusion

            return ai_data, violations

    # ============================================================
    # ANNOTATE FRAME (Fast <0.5ms OpenCV drawing onto any resolution)
    # ============================================================

    def annotate_frame(self, frame, ai_data: Optional[dict] = None):
        """
        Draw bounding boxes and zone overlay onto frame in <0.5ms using normalized boxes.
        """
        data = ai_data if ai_data is not None else {
            "boxes_to_draw": self._cached_boxes_to_draw,
            "heads_to_draw": self._cached_heads_to_draw,
            "helmets_to_draw": self._cached_helmets_to_draw,
            "active_intrusion": self._cached_active_intrusion,
        }

        active_intrusion = data.get("active_intrusion", False)
        frame = draw_zone(frame, zone_norm=self.zone_coords, alert=active_intrusion)
        fh, fw = frame.shape[:2]

        for norm_box, color, label, conf, small in data.get("boxes_to_draw", []):
            coords = [norm_box[0] * fw, norm_box[1] * fh, norm_box[2] * fw, norm_box[3] * fh]
            self._draw_box(frame, coords, color, label, conf, small=small)

        for norm_box, color, label, conf, small in data.get("heads_to_draw", []):
            coords = [norm_box[0] * fw, norm_box[1] * fh, norm_box[2] * fw, norm_box[3] * fh]
            self._draw_box(frame, coords, color, label, conf, small=small)

        for norm_box, color, label, conf, small in data.get("helmets_to_draw", []):
            coords = [norm_box[0] * fw, norm_box[1] * fh, norm_box[2] * fw, norm_box[3] * fh]
            self._draw_box(frame, coords, color, label, conf, small=small)

        return frame

    def process_frame(self, frame, run_inference: bool = True):
        """Unified wrapper for synchronous or interpolated inference."""
        if run_inference:
            ai_data, violations = self.analyze_frame(frame)
            return self.annotate_frame(frame, ai_data), violations
        else:
            return self.annotate_frame(frame), []

    # ============================================================
    # HELMET OVERLAP CHECK
    # ============================================================

    def _person_has_helmet(self, person_box, heads, helmets):
        """Determine if person is wearing a certified safety helmet."""
        px1, py1, px2, py2 = person_box
        pw = max(1.0, px2 - px1)
        ph = max(1.0, py2 - py1)
        head_region = (px1 - pw * 0.10, py1 - ph * 0.10, px2 + pw * 0.10, py1 + ph * 0.45)

        p_helmets = [
            h for h in helmets
            if self._iou(head_region, h[0]) > 0.05 or
            (px1 <= (h[0][0] + h[0][2]) * 0.5 <= px2 and py1 <= (h[0][1] + h[0][3]) * 0.5 <= py1 + ph * 0.45)
        ]

        p_heads = [
            h for h in heads
            if self._iou(head_region, h[0]) > 0.05 or
            (px1 <= (h[0][0] + h[0][2]) * 0.5 <= px2 and py1 <= (h[0][1] + h[0][3]) * 0.5 <= py1 + ph * 0.45)
        ]

        if not p_helmets and not p_heads:
            return False

        if p_heads and not p_helmets:
            return False

        if p_helmets and not p_heads:
            return True

        max_helm_conf = max(h[1] for h in p_helmets)
        max_head_conf = max(h[1] for h in p_heads)
        return max_helm_conf > (max_head_conf + 0.10)

    @classmethod
    def _nms_boxes(cls, candidates, iou_thresh=0.35):
        """Non-maximum suppression to merge overlapping candidate boxes."""
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
    def _iou(box1, box2):
        """Intersection-over-Union."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
        area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
        union = area1 + area2 - intersection

        return (intersection / union) if union > 0 else 0.0

    @staticmethod
    def _draw_box(frame, box, color, label, confidence, small=False):
        """Draw bounding box with header label."""
        x1, y1, x2, y2 = [int(v) for v in box]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2 if small else 3)

        text = f"{label} {confidence:.2f}"
        font_scale = 0.42 if small else 0.58
        font_thick = 1 if small else 2

        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thick)
        label_y = max(y1, th + 8)

        cv2.rectangle(
            frame,
            (x1, label_y - th - 5),
            (x1 + tw + 6, label_y + 4),
            color,
            -1,
        )
        cv2.putText(
            frame,
            text,
            (x1 + 3, label_y - 1),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            font_thick,
            lineType=cv2.LINE_AA,
        )


# ============================================================
# ASYNCHRONOUS INFERENCE WORKER (Thread-Safe Single Frame Slot)
# ============================================================

class AsyncInferenceWorker:
    """
    Decoupled background worker for AI inference.
    Maintains a single-element latest frame slot with zero queue backlog.
    Executes heavy YOLO inference asynchronously while the main display loop
    runs continuously at ~40 FPS.
    """

    def __init__(self, detector: SafeZoneDetector):
        self.detector = detector
        self.lock = threading.Lock()
        self.new_frame_event = threading.Event()
        self._latest_frame = None
        self.running = True

        self.latest_ai_data = {
            "boxes_to_draw": [],
            "heads_to_draw": [],
            "helmets_to_draw": [],
            "active_intrusion": False,
        }
        self.new_violations: List[Violation] = []
        self.ai_inference_count = 0
        self.ai_start_time = time.perf_counter()
        self.ai_fps = 0.0
        self.last_infer_duration = 0.0

        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def submit_frame(self, frame):
        """Submit frame to latest frame slot (non-blocking, overwrites old frame)."""
        if not self.running or frame is None:
            return
        with self.lock:
            self._latest_frame = frame
        self.new_frame_event.set()

    def _worker_loop(self):
        while self.running:
            if not self.new_frame_event.wait(timeout=0.03):
                continue
            self.new_frame_event.clear()

            with self.lock:
                frame = self._latest_frame
                self._latest_frame = None

            if frame is None or not self.running:
                continue

            t0 = time.perf_counter()
            ai_data, violations = self.detector.analyze_frame(frame)
            infer_dur = time.perf_counter() - t0

            with self.lock:
                self.latest_ai_data = ai_data
                if violations:
                    self.new_violations.extend(violations)
                self.last_infer_duration = infer_dur
                self.ai_inference_count += 1
                elapsed = time.perf_counter() - self.ai_start_time
                if elapsed >= 0.5:
                    self.ai_fps = self.ai_inference_count / elapsed
                    self.ai_inference_count = 0
                    self.ai_start_time = time.perf_counter()

    def get_latest_result(self) -> Tuple[dict, List[Violation], float, float]:
        """Retrieve latest annotations & new violations (non-blocking, <0.01ms)."""
        with self.lock:
            violations_copy = list(self.new_violations)
            self.new_violations.clear()
            return self.latest_ai_data, violations_copy, self.ai_fps, self.last_infer_duration

    def stop(self):
        """Cleanly stop worker thread."""
        self.running = False
        self.new_frame_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=0.3)