"""
HazardLens — Restricted-Zone Utilities
-----------------------------------------
Defines the restricted "danger zone" as a polygon on the video frame
and provides helpers to check whether a detected person is inside it.

IMPORTANT — RESOLUTION-INDEPENDENT ZONE:
    Zone coordinates are stored as NORMALIZED values (0.0 to 1.0),
    representing proportions of the frame width and height.

    This means the same zone definition works with ANY video resolution
    (e.g. 1280×720, 1920×1080, 2560×1440).

CALIBRATION:
    Run the calibration tool to define the zone for your video:

        python zone_utils.py path/to/your_video.mp4

    1. A window opens showing the first frame with dimensions displayed.
    2. Left-click to add polygon vertices (they are connected in order).
    3. Right-click to close the polygon and finish.
    4. Or press 'q' to finish with the current points.
    5. Copy the printed NORMALIZED coordinates into RESTRICTED_ZONE below.
"""

import sys
import cv2
import numpy as np
from shapely.geometry import Point, Polygon


# ════════════════════════════════════════════════════════════════
# DEFAULT RESTRICTED ZONE — NORMALIZED COORDINATES
# ════════════════════════════════════════════════════════════════
# Values are proportions of (frame_width, frame_height), ranging
# from 0.0 (left/top edge) to 1.0 (right/bottom edge).
#
# This default zone covers roughly the right ~35% of the frame,
# from ~14% to ~96% vertically.  It works with any resolution.
#
# ⚠  REPLACE these using the calibration tool for your specific
#    video/camera setup.
# ════════════════════════════════════════════════════════════════

ZONE_PRESETS = {
    "Active Work Site (Default)": [
        (0.08, 0.05),    # top-left of zone
        (0.92, 0.05),    # top-right
        (0.92, 0.98),    # bottom-right
        (0.08, 0.98),    # bottom-left
    ],
    "Center & Right Work Area": [
        (0.30, 0.08),
        (0.95, 0.08),
        (0.95, 0.98),
        (0.30, 0.98),
    ],
    "Entire Frame (100% Site)": [
        (0.01, 0.01),
        (0.99, 0.01),
        (0.99, 0.99),
        (0.01, 0.99),
    ],
}

RESTRICTED_ZONE = ZONE_PRESETS["Active Work Site (Default)"]


# ════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════

def _zone_to_pixels(frame_w, frame_h, zone_norm=None):
    """
    Convert normalized zone coordinates to absolute pixel coordinates.

    Parameters
    ----------
    frame_w, frame_h : int
        The video frame dimensions in pixels.
    zone_norm : list of (float, float), optional
        Normalized polygon vertices. Defaults to RESTRICTED_ZONE.

    Returns
    -------
    list of (int, int)
        Pixel coordinates for the polygon.
    """
    if zone_norm is None:
        zone_norm = RESTRICTED_ZONE
    return [(int(x * frame_w), int(y * frame_h)) for x, y in zone_norm]


def is_inside_zone(point, frame_w, frame_h, zone_norm=None):
    """
    Check whether *point* is inside the restricted zone polygon.

    Parameters
    ----------
    point : tuple (x, y)
        Pixel coordinates.
    frame_w, frame_h : int
        Video frame dimensions.
    zone_norm : list of (float, float), optional
        Normalized polygon vertices. Defaults to RESTRICTED_ZONE.

    Returns
    -------
    bool
    """
    if zone_norm is None:
        zone_norm = RESTRICTED_ZONE
    if len(zone_norm) < 3:
        return False
    zone_px = _zone_to_pixels(frame_w, frame_h, zone_norm)
    return Polygon(zone_px).contains(Point(point))


def is_person_in_zone(box, frame_w, frame_h, zone_norm=None):
    """
    Check whether a person's bounding box is inside (or intersects) the restricted zone.

    Performs multi-point validation:
      1. Bottom-center (feet position)
      2. Geometric center of person
      3. Bounding box intersection with zone polygon (>15% overlap)

    This ensures reliable detection even when feet are cut off by the camera edge,
    scaffolding, or waist-up framing.
    """
    if zone_norm is None:
        zone_norm = RESTRICTED_ZONE
    if len(zone_norm) < 3:
        return False

    zone_px = _zone_to_pixels(frame_w, frame_h, zone_norm)
    poly = Polygon(zone_px)
    x1, y1, x2, y2 = box

    # 1. Check foot position
    foot = Point((x1 + x2) / 2, y2)
    if poly.contains(foot):
        return True

    # 2. Check box center
    center = Point((x1 + x2) / 2, (y1 + y2) / 2)
    if poly.contains(center):
        return True

    # 3. Check bounding box intersection
    box_poly = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
    if poly.intersects(box_poly):
        try:
            inter_area = poly.intersection(box_poly).area
            box_area = max(1.0, (x2 - x1) * (y2 - y1))
            if (inter_area / box_area) > 0.15:
                return True
        except Exception:
            return True

    return False


def bbox_bottom_center(box):
    """
    Convert (x1, y1, x2, y2) to the bottom-center point (x, y).

    This approximates the person's foot position.
    """
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, y2)


def draw_zone(frame, zone_norm=None, color=(0, 165, 255), alert=False):
    """
    Draw a semi-transparent restricted-zone polygon on the frame.
    Scales automatically to any frame resolution.

    If alert=True, border turns red to highlight an active intrusion.
    """
    if zone_norm is None:
        zone_norm = RESTRICTED_ZONE
    if len(zone_norm) < 3:
        return frame

    h, w = frame.shape[:2]
    zone_px = _zone_to_pixels(w, h, zone_norm)
    pts = np.array(zone_px, dtype=np.int32).reshape((-1, 1, 2))

    draw_color = (0, 0, 255) if alert else color
    thickness = 3 if alert else 2

    # Outline
    cv2.polylines(frame, [pts], isClosed=True, color=draw_color, thickness=thickness)

    # Semi-transparent fill
    overlay = frame.copy()
    cv2.fillPoly(overlay, [pts], draw_color)
    opacity = 0.20 if alert else 0.12
    cv2.addWeighted(overlay, opacity, frame, 1.0 - opacity, 0, frame)

    # Label on top-left of zone
    min_x = min(p[0] for p in zone_px)
    min_y = min(p[1] for p in zone_px)
    label_text = "RESTRICTED ZONE [INTRUSION]" if alert else "RESTRICTED SITE ZONE"
    
    cv2.putText(
        frame,
        label_text,
        (min_x + 10, max(min_y + 25, 30)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        draw_color,
        2,
    )

    return frame


# ════════════════════════════════════════════════════════════════
# CALIBRATION TOOL
# ════════════════════════════════════════════════════════════════
# Run this file directly with a video path to interactively
# select the restricted-zone polygon:
#
#     python zone_utils.py path/to/video.mp4
#
# Left-click  → add point
# Right-click → close polygon and finish
# 'q' key     → finish with current points
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python zone_utils.py path/to/video.mp4")
        print("       Opens the first frame for interactive zone selection.")
        sys.exit(0)

    video_path = sys.argv[1]
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"ERROR: Could not read the first frame of '{video_path}'.")
        sys.exit(1)

    frame_h, frame_w = frame.shape[:2]
    print(f"\n{'='*50}")
    print(f"  ZONE CALIBRATION TOOL")
    print(f"{'='*50}")
    print(f"  Frame size: {frame_w} × {frame_h}")
    print(f"  Left-click:  add polygon point")
    print(f"  Right-click: close polygon & finish")
    print(f"  'q' key:     finish with current points")
    print(f"{'='*50}\n")

    points_px = []     # absolute pixel coordinates (for drawing)
    display = frame.copy()

    # Show frame dimensions in the corner
    cv2.putText(
        display, f"Frame: {frame_w}x{frame_h}",
        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
    )

    def click_event(event, x, y, flags, param):
        global display

        if event == cv2.EVENT_LBUTTONDOWN:
            # ── Validate bounds ─────────────────────────────────
            if x < 0 or x >= frame_w or y < 0 or y >= frame_h:
                print(f"  ⚠  Point ({x}, {y}) is outside the frame!")
                return

            points_px.append((x, y))
            norm_x = round(x / frame_w, 4)
            norm_y = round(y / frame_h, 4)
            print(f"  Point {len(points_px)}: pixel ({x}, {y}) → normalized ({norm_x}, {norm_y})")

            # Redraw
            display = frame.copy()
            cv2.putText(
                display, f"Frame: {frame_w}x{frame_h}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
            )
            for i, pt in enumerate(points_px):
                cv2.circle(display, pt, 6, (0, 0, 255), -1)
                cv2.putText(
                    display, str(i + 1),
                    (pt[0] + 10, pt[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2,
                )
            if len(points_px) > 1:
                for i in range(len(points_px) - 1):
                    cv2.line(display, points_px[i], points_px[i + 1], (0, 255, 0), 2)
            cv2.imshow("Zone Calibration — click points, right-click to finish", display)

        elif event == cv2.EVENT_RBUTTONDOWN:
            # Close polygon
            if len(points_px) >= 3:
                cv2.line(display, points_px[-1], points_px[0], (0, 255, 0), 2)
                cv2.imshow("Zone Calibration — click points, right-click to finish", display)
                print("\n  Polygon closed.")
                cv2.waitKey(500)
                cv2.destroyAllWindows()

    window_name = "Zone Calibration — click points, right-click to finish"
    cv2.imshow(window_name, display)
    cv2.setMouseCallback(window_name, click_event)

    while True:
        key = cv2.waitKey(100) & 0xFF
        if key == ord('q'):
            break
        # Check if window was closed by right-click callback
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

    cv2.destroyAllWindows()

    # ── Output ──────────────────────────────────────────────────
    if len(points_px) < 3:
        print("\n  ⚠  Need at least 3 points to define a polygon.")
        print("  No zone saved.")
    else:
        # Convert to normalized coordinates
        points_norm = [
            (round(x / frame_w, 4), round(y / frame_h, 4))
            for x, y in points_px
        ]

        print(f"\n{'='*50}")
        print(f"  CALIBRATION COMPLETE")
        print(f"{'='*50}")
        print(f"  Video:      {frame_w} × {frame_h}")
        print(f"  Points:     {len(points_px)}")
        print()
        print("  Copy this into RESTRICTED_ZONE in zone_utils.py:")
        print()
        print(f"  RESTRICTED_ZONE = {points_norm}")
        print()
        print("  These are NORMALIZED coordinates (0.0–1.0) and will")
        print("  automatically scale to any video resolution.")
        print()
