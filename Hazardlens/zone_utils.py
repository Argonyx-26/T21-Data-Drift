"""
SafeZone AI - Restricted Zone Utilities
-----------------------------------------
Defines the restricted "danger zone" as a polygon on the video frame,
and provides a helper to check whether a detected person is inside it.

HOW TO CALIBRATE THE ZONE FOR YOUR DEMO VIDEO:
1. Run `python zone_utils.py path/to/your_video.mp4` - this opens the
   first frame and lets you click 4+ points to define the zone.
2. Click points in order (they'll be connected as a polygon), then
   press 'q' to print the coordinates.
3. Copy the printed coordinates into RESTRICTED_ZONE below.
"""

import sys
import cv2
from shapely.geometry import Point, Polygon

# Default placeholder zone (a rectangle roughly in the center-right of
# a 1280x720 frame). REPLACE these coordinates using the calibration
# tool below, based on your actual demo video/camera resolution.
RESTRICTED_ZONE = [
    (640, 200),
    (1100, 200),
    (1100, 600),
    (640, 600),
]


def is_inside_zone(point, zone=RESTRICTED_ZONE):
    """
    point: (x, y) tuple - typically the bottom-center of a person's
           bounding box (their approximate foot position)
    zone:  list of (x, y) tuples defining the polygon
    Returns True if the point is inside the restricted zone.
    """
    return Polygon(zone).contains(Point(point))


def bbox_bottom_center(box):
    """box: (x1, y1, x2, y2) -> returns (x, y) at the bottom-center."""
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, y2)


def draw_zone(frame, zone=RESTRICTED_ZONE, color=(0, 165, 255)):
    """Draws the restricted zone polygon on a frame for visualization."""
    import numpy as np
    pts = np.array(zone, dtype=int).reshape((-1, 1, 2))
    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
    overlay = frame.copy()
    cv2.fillPoly(overlay, [pts], color)
    cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
    return frame


# --- Simple calibration tool ---
# Run this file directly with a video path to click-select zone points:
#   python zone_utils.py your_video.mp4
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python zone_utils.py path/to/video.mp4")
        sys.exit(0)

    video_path = sys.argv[1]
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Could not read the first frame of that video.")
        sys.exit(1)

    points = []

    def click_event(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((x, y))
            cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
            if len(points) > 1:
                cv2.line(frame, points[-2], points[-1], (0, 255, 0), 2)
            cv2.imshow("Click zone corners, then press q", frame)

    cv2.imshow("Click zone corners, then press q", frame)
    cv2.setMouseCallback("Click zone corners, then press q", click_event)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("\nCopy this into RESTRICTED_ZONE in zone_utils.py:")
    print(points)
