"""
HazardLens — AI-Powered Workplace Safety Monitoring
----------------------------------------------------
Streamlit dashboard for real-time PPE compliance and restricted-zone monitoring.
Features:
  • Fixed top clearance (padding-top: 3.5rem) preventing header chopping
  • Clean single file uploader (zero duplicate labels/buttons)
  • Compact desktop sidebar (270px)
  • HazardLens construction helmet/shield logo
  • Pixel-aligned compact header with live status pill
  • Perfectly matched vertical alignment between video viewport and statistics
  • Equal width, equal height, dynamically responsive PPE & Zone stat cards
  • Site Safety Inspector exact avatar card
  • Real-Time Violation & Event Log beneath the video viewport
  • 100% preservation of all detector, YOLO models, and backend logic
"""

import os
import time
import shutil
import base64
import cv2
import pandas as pd
import streamlit as st

from detector import SafeZoneDetector

PPE_WEIGHTS    = "best.pt"
PERSON_WEIGHTS = "yolov8n.pt"

# Asset Paths & Exact Reference Avatar Resolution
_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

LOGO_PATH = os.path.join(ASSETS_DIR, "logo.svg")
USER_REF_IMAGE = r"C:\Users\Chandana Bhat\.gemini\antigravity-ide\brain\7700f8b0-13b8-4377-9f90-7c073a1719d6\.user_uploaded\media_1790353220849.jpg"
LOCAL_AVATAR = os.path.join(ASSETS_DIR, "reference_avatar.jpg")

if os.path.exists(USER_REF_IMAGE) and not os.path.exists(LOCAL_AVATAR):
    try:
        shutil.copyfile(USER_REF_IMAGE, LOCAL_AVATAR)
    except Exception:
        pass

EXACT_AVATAR_PATH = LOCAL_AVATAR if os.path.exists(LOCAL_AVATAR) else (USER_REF_IMAGE if os.path.exists(USER_REF_IMAGE) else "")

st.set_page_config(
    page_title="HazardLens — AI Safety Monitoring",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded",
)

def get_base64_image(file_path: str) -> str:
    """Return base64 data URI for an image file."""
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(file_path)[1].lower().replace(".", "")
    mime = "svg+xml" if ext == "svg" else ("jpeg" if ext in ("jpg", "jpeg") else "png")
    return f"data:image/{mime};base64,{data}"

logo_b64 = get_base64_image(LOGO_PATH)


# ─────────────────────────────────────────────────────────────
# Custom CSS — Clean, Professional Desktop Stylesheet
# ─────────────────────────────────────────────────────────────

st.markdown("""<style>
/* Base Theme */
.stApp {
background-color: #FFFDF6 !important;
font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
color: #1A1A2E;
}

/* Proper Top Clearance for Streamlit Header Toolbar (fixes chopped header) */
.block-container {
padding-top: 3.5rem !important;
padding-bottom: 1.5rem !important;
padding-left: 1.5rem !important;
padding-right: 1.5rem !important;
max-width: 100% !important;
}

/* Column Top Reset for Pixel-Perfect Vertical Alignment */
[data-testid="column"] > div {
padding-top: 0 !important;
margin-top: 0 !important;
}

/* Responsive Desktop Sidebar */
@media (min-width: 992px) {
[data-testid="stSidebar"] {
min-width: 260px !important;
max-width: 275px !important;
width: 270px !important;
}
}
[data-testid="stSidebar"] {
background-color: #1A1A2E !important;
border-right: 1px solid rgba(255,255,255,0.08);
}
[data-testid="stSidebar"] * {
color: #D1D5DB !important;
font-family: 'Plus Jakarta Sans', sans-serif;
}
[data-testid="stSidebar"] .block-container {
padding: 1.2rem 1rem !important;
padding-top: 3.5rem !important;
}

/* Sidebar Branding */
.sb-brand {
font-family: 'Outfit', sans-serif;
font-size: 1.25rem;
font-weight: 800;
color: #FFFFFF !important;
padding-bottom: 0.5rem;
margin-bottom: 0.8rem;
border-bottom: 1px solid rgba(255,255,255,0.1);
line-height: 1;
display: flex;
align-items: center;
gap: 10px;
}
.sb-brand span {
color: #F5A623 !important;
}
.sb-logo {
width: 28px;
height: 28px;
object-fit: contain;
}

/* Sidebar Buttons */
[data-testid="stSidebar"] .stButton > button {
border-radius: 8px !important;
font-weight: 700 !important;
font-family: 'Outfit', sans-serif !important;
font-size: 0.88rem !important;
padding: 0.55rem 1rem !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-primary"],
[data-testid="stSidebar"] button[kind="primary"] {
background: linear-gradient(135deg, #F5A623 0%, #D97706 100%) !important;
color: #1A1A2E !important;
border: none !important;
box-shadow: 0 2px 10px rgba(245, 166, 35, 0.3) !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-secondary"],
[data-testid="stSidebar"] button[kind="secondary"] {
background: rgba(255,255,255,0.08) !important;
color: #FFFFFF !important;
border: 1px solid rgba(255,255,255,0.15) !important;
}

/* Main Dashboard Header */
.hz-header {
background-color: #1A1A2E;
border-left: 5px solid #F5A623;
border-radius: 10px;
padding: 12px 18px;
margin-bottom: 14px;
box-shadow: 0 4px 16px -4px rgba(26, 26, 46, 0.12);
display: flex;
align-items: center;
justify-content: space-between;
}
.hz-header-left {
display: flex;
align-items: center;
gap: 12px;
}
.hz-logo {
width: 36px;
height: 36px;
object-fit: contain;
}
.hz-header-text {
display: flex;
flex-direction: column;
}
.hz-title {
color: #FFFFFF;
font-family: 'Outfit', sans-serif;
font-size: 1.35rem;
font-weight: 800;
line-height: 1.2;
}
.hz-title .hz-accent {
color: #F5A623;
}
.hz-subtitle {
color: #9CA3AF;
font-size: 0.8rem;
font-family: 'Plus Jakarta Sans', sans-serif;
margin-top: 1px;
}

/* Status Pill */
.status-pill {
display: inline-flex;
align-items: center;
gap: 7px;
padding: 4px 12px;
border-radius: 20px;
font-family: 'Outfit', sans-serif;
font-size: 0.74rem;
font-weight: 700;
letter-spacing: 0.04em;
text-transform: uppercase;
white-space: nowrap;
}
.status-pill.active {
background-color: #ECFDF5;
color: #065F46;
border: 1px solid #A7F3D0;
}
.status-pill.inactive {
background-color: #F3F4F6;
color: #6B7280;
border: 1px solid #E5E7EB;
}
.pulse-dot {
width: 7px;
height: 7px;
border-radius: 50%;
background-color: #10B981;
}

/* Panel Headings: Equal Height for Pixel-Perfect Column Alignment */
.panel-heading {
font-family: 'Outfit', sans-serif;
font-size: 0.95rem;
font-weight: 700;
color: #1A1A2E;
margin: 0 0 8px 0 !important;
padding: 0 !important;
height: 28px;
line-height: 28px;
display: flex;
align-items: center;
gap: 7px;
}

/* Responsive Video Container */
.video-viewport {
background: #0E0F17;
border-radius: 10px;
border: 1px solid #E8E2D2;
overflow: hidden;
width: 100%;
display: flex;
justify-content: center;
align-items: center;
}
.video-viewport [data-testid="stImage"] img {
border-radius: 6px;
display: block;
width: 100% !important;
object-fit: contain;
}

/* Video Empty State */
.video-empty-box {
background: #FFFFFF;
border: 1.5px dashed #E2DCB8;
border-radius: 10px;
padding: 2.8rem 1.5rem;
text-align: center;
color: #6B7280;
width: 100%;
}
.ve-icon {
font-size: 2.5rem;
display: block;
margin-bottom: 0.4rem;
}
.ve-title {
font-family: 'Outfit', sans-serif;
font-size: 1.05rem;
font-weight: 700;
color: #1A1A2E;
margin-bottom: 0.2rem;
}
.ve-sub {
font-size: 0.82rem;
color: #6B7280;
}

/* Statistics Grid: Dynamic Responsive Equal Width & Height */
.stats-grid {
display: grid;
grid-template-columns: 1fr 1fr;
gap: 10px;
width: 100%;
margin-bottom: 0;
align-items: stretch;
}
.stat-card {
border-radius: 8px;
padding: 12px 14px;
box-sizing: border-box;
width: 100%;
min-height: 76px;
display: flex;
flex-direction: column;
justify-content: center;
color: #FFFFFF;
box-shadow: 0 3px 10px rgba(0,0,0,0.08);
}
.stat-ppe {
background: #C5283D;
}
.stat-zone {
background: #E8720C;
}
.sc-label {
font-family: 'Outfit', sans-serif;
font-size: 0.72rem;
font-weight: 700;
letter-spacing: 0.04em;
text-transform: uppercase;
color: #FFFFFF;
margin-bottom: 3px;
white-space: nowrap;
overflow: hidden;
text-overflow: ellipsis;
}
.sc-value {
font-family: 'Outfit', sans-serif;
font-size: 1.9rem;
font-weight: 800;
line-height: 1;
color: #FFFFFF;
}

/* Exact Reference Avatar Frame (Column 2) */
[data-testid="column"]:nth-of-type(2) [data-testid="stImage"] {
background: #FFFFFF;
border: 1px solid #E8E2D2;
border-radius: 8px;
padding: 6px;
overflow: hidden;
display: flex;
justify-content: center;
align-items: center;
box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
[data-testid="column"]:nth-of-type(2) [data-testid="stImage"] img {
border-radius: 6px;
max-height: 220px;
width: 100% !important;
object-fit: contain;
}

/* Violation Log */
.log-empty-box {
background: #FFFFFF;
border: 1px solid #E8E2D2;
border-radius: 8px;
padding: 1rem;
text-align: center;
color: #6B7280;
font-size: 0.82rem;
}
.stDataFrame {
border-radius: 8px !important;
overflow: hidden !important;
border: 1px solid #E5E0D0 !important;
background: #FFFFFF !important;
width: 100% !important;
}

/* Responsive columns gap */
[data-testid="stHorizontalBlock"] {
gap: 1.2rem !important;
}

@media (max-width: 1024px) {
.stats-grid {
grid-template-columns: 1fr;
}
}
</style>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Main Header (Logo + Title + Status Pill)
# ─────────────────────────────────────────────────────────────

if st.session_state.get("running", False):
    status_html = '<span class="status-pill active"><span class="pulse-dot"></span> MONITORING ACTIVE</span>'
else:
    status_html = '<span class="status-pill inactive">⏸ MONITORING INACTIVE</span>'

header_logo_tag = f'<img src="{logo_b64}" class="hz-logo" alt="Logo" />' if logo_b64 else '🦺'

header_html = (
    '<div class="hz-header">'
    '<div class="hz-header-left">'
    f'{header_logo_tag}'
    '<div class="hz-header-text">'
    '<div class="hz-title">Hazard<span class="hz-accent">Lens</span></div>'
    '<div class="hz-subtitle">AI-Powered Workplace Safety Monitoring</div>'
    '</div>'
    '</div>'
    f'<div class="hz-header-right">{status_html}</div>'
    '</div>'
)
st.markdown(header_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Sidebar (Single Clean File Uploader & Controls)
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    sb_logo_tag = f'<img src="{logo_b64}" class="sb-logo" alt="Logo" />' if logo_b64 else '🦺'
    st.markdown(f'<div class="sb-brand">{sb_logo_tag}Hazard<span>Lens</span></div>', unsafe_allow_html=True)

    # 1. Single Clean Native File Uploader (Zero duplicate labels or buttons)
    uploaded_file = st.file_uploader(
        "📹 Video Source",
        type=["mp4", "mov", "avi"],
        help="Upload MP4, MOV, or AVI video to inspect",
    )

    # 2. Confidence Slider
    conf_threshold = st.slider(
        "⚙️ Detection Confidence",
        min_value=0.1,
        max_value=0.9,
        value=0.4,
        step=0.05,
    )

    # 3. Restricted Zone Area
    zone_option = st.selectbox(
        "🚧 Restricted Zone Area",
        ["Active Work Site (Default)"],
    )

    # 4. Monitoring Controls
    st.markdown('<div style="margin-top: 0.6rem;"></div>', unsafe_allow_html=True)
    start_button = st.button("▶  Start Monitoring", use_container_width=True, type="primary")
    stop_button  = st.button("⏹  Stop", use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Session State Management
# ─────────────────────────────────────────────────────────────

if "violations" not in st.session_state:
    st.session_state.violations = []
if "running" not in st.session_state:
    st.session_state.running = False

if start_button:
    st.session_state.running = True
    st.session_state.violations = []

if stop_button:
    st.session_state.running = False


# ─────────────────────────────────────────────────────────────
# Main Layout:
# Left column (70%)  → Dominant Live Video Viewport + Real-Time Violation Log
# Right column (30%) → Live Statistics + Site Safety Inspector Avatar
# ─────────────────────────────────────────────────────────────

col_video, col_side = st.columns([2.3, 1.0])

with col_video:
    st.markdown('<div class="panel-heading">🎥 Live Safety Monitoring</div>', unsafe_allow_html=True)
    video_placeholder = st.empty()

    st.markdown('<div class="panel-heading" style="margin-top:14px;">📋 Real-Time Violation & Event Log</div>', unsafe_allow_html=True)
    log_placeholder = st.empty()

with col_side:
    st.markdown('<div class="panel-heading">📊 Live Statistics</div>', unsafe_allow_html=True)
    stats_placeholder = st.empty()

    st.markdown('<div class="panel-heading" style="margin-top:14px;">👷 Site Safety Inspector</div>', unsafe_allow_html=True)
    if EXACT_AVATAR_PATH and os.path.exists(EXACT_AVATAR_PATH):
        st.image(EXACT_AVATAR_PATH, use_container_width=True)


def render_stat_cards(ppe_count: int, zone_count: int):
    """Render equal-width, equal-height statistics cards with zero text wrapping."""
    html = (
        '<div class="stats-grid">'
        '<div class="stat-card stat-ppe">'
        '<div class="sc-label">🪖 PPE VIOLATIONS</div>'
        f'<div class="sc-value">{ppe_count}</div>'
        '</div>'
        '<div class="stat-card stat-zone">'
        '<div class="sc-label">🚧 ZONE INTRUSIONS</div>'
        f'<div class="sc-value">{zone_count}</div>'
        '</div>'
        '</div>'
    )
    stats_placeholder.markdown(html, unsafe_allow_html=True)


def render_log(violations: list):
    """Render real violation log table."""
    if not violations:
        log_placeholder.markdown(
            '<div class="log-empty-box">🛡️ No violations detected yet.<br><span style="font-size:0.76rem;color:#9CA3AF;">Active video stream will record unauthorized intrusions and PPE events here.</span></div>',
            unsafe_allow_html=True
        )
        return

    display_data = violations[::-1][:50]
    df = pd.DataFrame(display_data)

    log_placeholder.dataframe(
        df,
        hide_index=True,
        height=200,
        use_container_width=True,
    )


# Initial render of stats and log
render_stat_cards(0, 0)
render_log(st.session_state.violations)


# ─────────────────────────────────────────────────────────────
# Real-Time Video Monitoring Loop (Fast & Preserved)
# ─────────────────────────────────────────────────────────────

if st.session_state.running:

    if uploaded_file is None:
        st.warning("Please upload a video file in the sidebar to begin monitoring.")
        st.session_state.running = False
        st.stop()

    try:
        detector = SafeZoneDetector(
            ppe_weights=PPE_WEIGHTS,
            person_weights=PERSON_WEIGHTS,
            conf_threshold=conf_threshold,
        )
    except Exception as e:
        st.error(f"Could not load detector models ({PPE_WEIGHTS}, {PERSON_WEIGHTS}): {e}")
        st.session_state.running = False
        st.stop()

    temp_path = "temp_uploaded_video.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    cap = cv2.VideoCapture(temp_path)

    ppe_count = 0
    zone_count = 0
    last_rendered_counts = (-1, -1)
    last_log_count = -1

    while cap.isOpened() and st.session_state.running:
        ret, frame = cap.read()
        if not ret:
            break

        # Run real YOLO + polygon detection logic
        annotated_frame, violations = detector.process_frame(frame)

        for v in violations:
            st.session_state.violations.append({
                "Time": time.strftime("%H:%M:%S", time.localtime(v.timestamp)),
                "Type": v.type,
                "Confidence": f"{v.confidence:.2f}",
                "Details": v.details,
            })
            if v.type == "PPE":
                ppe_count += 1
            elif v.type == "ZONE":
                zone_count += 1

        # Display processed frame with real YOLO bounding boxes and zone overlay
        video_placeholder.image(
            cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB),
            channels="RGB",
            use_container_width=True,
        )

        # Performance: Only re-render when counts change
        if (ppe_count, zone_count) != last_rendered_counts:
            render_stat_cards(ppe_count, zone_count)
            last_rendered_counts = (ppe_count, zone_count)

        # Performance: Only re-render log when new events arrive
        if len(st.session_state.violations) != last_log_count:
            render_log(st.session_state.violations)
            last_log_count = len(st.session_state.violations)

    cap.release()

    if ppe_count == 0 and zone_count == 0:
        st.info("Video processing complete. Zero safety violations detected.")
    else:
        st.success(f"Video monitoring complete. PPE Violations: {ppe_count} | Zone Intrusions: {zone_count}")

else:
    empty_video_html = (
        '<div class="video-empty-box">'
        '<div class="ve-icon">🎥</div>'
        '<div class="ve-title">Live Safety Monitoring Viewport</div>'
        '<div class="ve-sub">Upload a video in the sidebar and click <strong>▶ Start Monitoring</strong> to begin real-time detection.</div>'
        '</div>'
    )
    video_placeholder.markdown(empty_video_html, unsafe_allow_html=True)
