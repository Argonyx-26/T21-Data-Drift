"""
HazardLens — Live Dashboard
-------------------------------
Streamlit app: upload a video file, see PPE and zone violations flagged
in real time as it plays, and view a running violation log.

HOW TO RUN:
    streamlit run app.py

BEFORE RUNNING:
    Make sure best.pt (custom YOLO weights) and yolov8n.pt (pretrained)
    are in the same folder, or update the paths below.
"""

import time
import cv2
import pandas as pd
import streamlit as st

from detector import SafeZoneDetector

PPE_WEIGHTS    = "best.pt"
PERSON_WEIGHTS = "yolov8n.pt"

st.set_page_config(page_title="HazardLens", page_icon="🦺", layout="wide")

# ─────────────────────────────────────────────────────────────
# Custom styling
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
    :root {
        --safety-orange: #FF6B35;
        --navy: #1A1A2E;
        --navy-light: #22223A;
    }

    .stApp {
        background-color: #F5F5F7;
    }

    .sz-header {
        background: linear-gradient(90deg, var(--navy) 0%, var(--navy-light) 100%);
        padding: 1.4rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.2rem;
        border-left: 6px solid var(--safety-orange);
    }
    .sz-header h1 {
        color: white;
        margin: 0;
        font-size: 1.8rem;
    }
    .sz-header p {
        color: #C9C9D4;
        margin: 0.2rem 0 0 0;
        font-size: 0.95rem;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-live {
        background-color: #E8F8EE;
        color: #1B7F3E;
    }
    .status-stopped {
        background-color: #F0F0F2;
        color: #6B6B76;
    }
    .pulse-dot {
        width: 9px; height: 9px; border-radius: 50%;
        background-color: #22C55E;
        box-shadow: 0 0 0 0 rgba(34,197,94, 0.7);
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0%   { box-shadow: 0 0 0 0 rgba(34,197,94, 0.6); }
        70%  { box-shadow: 0 0 0 8px rgba(34,197,94, 0); }
        100% { box-shadow: 0 0 0 0 rgba(34,197,94, 0); }
    }

    .stat-card {
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.8rem;
        color: white;
    }
    .stat-card .label {
        font-size: 0.8rem;
        opacity: 0.85;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .stat-card .value {
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .card-ppe  { background: linear-gradient(135deg, #D7263D 0%, #A31621 100%); }
    .card-zone { background: linear-gradient(135deg, #FF9F1C 0%, #E8720C 100%); }

    section[data-testid="stSidebar"] {
        background-color: var(--navy);
    }
    section[data-testid="stSidebar"] * {
        color: #EDEDF2 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="sz-header">
    <h1>🦺 HazardLens</h1>
    <p>Real-time PPE compliance and restricted-zone monitoring</p>
</div>
""", unsafe_allow_html=True)

import os
from zone_utils import ZONE_PRESETS

# ─────────────────────────────────────────────────────────────
# Sidebar controls
# ─────────────────────────────────────────────────────────────

st.sidebar.header("⚙️ Controls")
uploaded_file  = st.sidebar.file_uploader("Upload a video", type=["mp4", "mov", "avi"])
conf_threshold = st.sidebar.slider("Detection confidence", 0.1, 0.9, 0.4, 0.05)

zone_preset_name = st.sidebar.selectbox(
    "📐 Restricted Zone Area",
    list(ZONE_PRESETS.keys()),
    index=0,
)
selected_zone = ZONE_PRESETS[zone_preset_name]

start_button   = st.sidebar.button("▶  Start monitoring", use_container_width=True)
stop_button    = st.sidebar.button("⏹  Stop", use_container_width=True)

# ─────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────

if "violations" not in st.session_state:
    st.session_state.violations = []
if "running" not in st.session_state:
    st.session_state.running = False

if start_button:
    st.session_state.running = True
    # Clear old violations when starting a new monitoring session
    st.session_state.violations = []

if stop_button:
    st.session_state.running = False

# ─────────────────────────────────────────────────────────────
# Status badge
# ─────────────────────────────────────────────────────────────

if st.session_state.running:
    st.markdown(
        '<span class="status-badge status-live">'
        '<span class="pulse-dot"></span> MONITORING ACTIVE</span>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<span class="status-badge status-stopped">⏸ STOPPED</span>',
        unsafe_allow_html=True,
    )

st.write("")

# ─────────────────────────────────────────────────────────────
# Layout: video on the left, metrics + log on the right
# ─────────────────────────────────────────────────────────────

col_video, col_stats = st.columns([2, 1])

with col_video:
    video_placeholder = st.empty()

with col_stats:
    st.subheader("Live stats")

    stat_col1, stat_col2 = st.columns(2)
    metric_ppe_placeholder  = stat_col1.empty()
    metric_zone_placeholder = stat_col2.empty()

    def render_stat_cards(ppe_count: int, zone_count: int):
        """Render the PPE and zone violation count cards."""
        metric_ppe_placeholder.markdown(f"""
        <div class="stat-card card-ppe">
            <div class="label">🪖 PPE Violations</div>
            <div class="value">{ppe_count}</div>
        </div>
        """, unsafe_allow_html=True)
        metric_zone_placeholder.markdown(f"""
        <div class="stat-card card-zone">
            <div class="label">🚧 Zone Intrusions</div>
            <div class="value">{zone_count}</div>
        </div>
        """, unsafe_allow_html=True)

    render_stat_cards(0, 0)

    st.subheader("Violation log")
    log_placeholder = st.empty()


def render_log(violations: list):
    """
    Render the violation log as a native Streamlit dataframe.

    Uses st.dataframe() instead of raw HTML to avoid rendering
    issues where HTML tags appear as text.
    """
    if not violations:
        log_placeholder.info("No violations logged yet.")
        return

    # Show newest violations first, limit to 50
    display_data = violations[::-1][:50]
    df = pd.DataFrame(display_data)

    log_placeholder.dataframe(
        df,
        hide_index=True,
        height=320,
    )


render_log(st.session_state.violations)

# ─────────────────────────────────────────────────────────────
# Main monitoring loop
# ─────────────────────────────────────────────────────────────

if st.session_state.running:

    # ── Load detector ──────────────────────────────────────────
    try:
        detector = SafeZoneDetector(
            ppe_weights=PPE_WEIGHTS,
            person_weights=PERSON_WEIGHTS,
            conf_threshold=conf_threshold,
            zone_coords=selected_zone,
        )
    except Exception as e:
        st.error(
            f"Could not load model weights. Make sure '{PPE_WEIGHTS}' "
            f"and '{PERSON_WEIGHTS}' are in the project folder.\n\n{e}"
        )
        st.stop()

    # ── Load video ─────────────────────────────────────────────
    if uploaded_file is None:
        if os.path.exists("temp_uploaded_video.mp4"):
            temp_path = "temp_uploaded_video.mp4"
        elif os.path.exists("demo.mp4"):
            temp_path = "demo.mp4"
        else:
            st.warning("Please upload a video file in the sidebar first.")
            st.stop()
    else:
        temp_path = "temp_uploaded_video.mp4"
        uploaded_file.seek(0)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())

    cap = cv2.VideoCapture(temp_path)

    ppe_count  = 0
    zone_count = 0

    # ── Process frames ─────────────────────────────────────────
    while cap.isOpened() and st.session_state.running:
        ret, frame = cap.read()
        if not ret:
            break

        annotated_frame, violations = detector.process_frame(frame)

        # ── Record new violation events ────────────────────────
        for v in violations:
            st.session_state.violations.append({
                "Time":       time.strftime("%H:%M:%S", time.localtime(v.timestamp)),
                "Type":       v.type,
                "Confidence": f"{v.confidence:.2f}",
                "Details":    v.details,
            })
            if v.type == "INTRUSION":
                zone_count += 1
                ppe_count += 1
            elif v.type == "PPE":
                ppe_count += 1
            elif v.type == "ZONE":
                zone_count += 1

        # ── Update display ─────────────────────────────────────
        video_placeholder.image(
            cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB),
            channels="RGB",
            use_container_width=True,
        )

        render_stat_cards(ppe_count, zone_count)
        render_log(st.session_state.violations)

        time.sleep(0.03)

    cap.release()

    # ── End of video ───────────────────────────────────────────
    if ppe_count == 0 and zone_count == 0:
        st.info("Video processing complete. No violations detected.")
    else:
        st.success(
            f"Video processing complete. "
            f"PPE violations: {ppe_count} | Zone intrusions: {zone_count}"
        )

else:
    video_placeholder.info("Click **Start monitoring** in the sidebar to begin.")
