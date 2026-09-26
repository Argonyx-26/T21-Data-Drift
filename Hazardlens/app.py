"""
HazardLens — AI-Powered Workplace Safety Monitoring
----------------------------------------------------
Streamlit dashboard for real-time PPE compliance and restricted-zone monitoring.
Features:
  • Decoupled 30–40 FPS continuous video display pipeline
  • Asynchronous background AI inference worker
  • High-contrast, bold dark navy headers (1.3rem, #1A1A2E)
  • Fixed sidebar icons (native Material Symbols font support with zero raw ligature text)
  • Collision-free, perfectly spaced sidebar video uploader
  • Ultra-fast AI inference pipeline with st.cache_resource model caching
  • Optimized resolution (imgsz=320)
  • Real-time FPS monitoring indicator integrated into header status
  • Seamless HazardLens branding everywhere with zero whitespace
  • Card-style containers with rounded corners, subtle shadows, and borders
  • Real-time Violation Log table with zero blank trailing rows, auto-height & badges
  • 100% preservation of all detector models, YOLO tracking, and backend logic
"""

import os
import time
import shutil
import base64
import importlib
import html
import cv2
import pandas as pd
import streamlit as st

import detector
import zone_utils
importlib.reload(detector)
importlib.reload(zone_utils)

from detector import (
    SafeZoneDetector,
    AsyncInferenceWorker,
    load_cached_yolo_models,
    get_optimal_device,
)
from zone_utils import ZONE_PRESETS

PPE_WEIGHTS    = "best.pt"
PERSON_WEIGHTS = "yolov8n.pt"

INFERENCE_IMGSZ = 320
MAX_PROCESSING_WIDTH = 720

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
# Custom CSS — Clean, High-Contrast Desktop Stylesheet
# ─────────────────────────────────────────────────────────────

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

:root {
    --text-color: #1A1A2E !important;
    --background-color: #FFFDF6 !important;
    --secondary-background-color: #FFFFFF !important;
}

/* Base Theme */
.stApp {
    background-color: #FFFDF6 !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #1A1A2E !important;
}

/* Ensure high contrast dark navy for all main content typography */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp label {
    color: #1A1A2E;
}

/* Protect Material Icons & Symbols */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] *,
[data-testid="collapsedControl"],
[data-testid="collapsedControl"] *,
[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
.material-icons,
[data-testid="stSidebar"] [data-testid="stIconMaterial"],
[data-testid="stSidebar"] .material-symbols-rounded,
[data-testid="stSidebar"] .material-symbols-outlined {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
    font-style: normal !important;
    font-weight: normal !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    display: inline-block !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-feature-settings: 'liga' !important;
    font-feature-settings: 'liga' !important;
    -webkit-font-smoothing: antialiased !important;
}

/* Proper Top Clearance for Streamlit Header Toolbar */
.block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 1.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
}

/* Pixel-Perfect Column Alignment & Top Reset */
[data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
    gap: 1.4rem !important;
}

[data-testid="column"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

[data-testid="column"] > div {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

[data-testid="column"] [data-testid="stVerticalBlock"] {
    gap: 0 !important;
    padding-top: 0 !important;
    margin-top: 0 !important;
}

[data-testid="column"] [data-testid="element-container"] {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

[data-testid="column"] [data-testid="element-container"]:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

.stMarkdown {
    margin: 0 !important;
    padding: 0 !important;
}

.stMarkdown > div > p {
    margin: 0 !important;
    padding: 0 !important;
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
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox,
[data-testid="stSidebar"] .stSlider {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
[data-testid="stSidebar"] label p {
    color: #D1D5DB !important;
}
[data-testid="stSidebar"] .block-container {
    padding: 1.2rem 1rem !important;
    padding-top: 3.5rem !important;
}

/* Sidebar Branding — HazardLens with Zero Whitespace */
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
.sb-brand-text {
    display: inline-block !important;
    color: #FFFFFF !important;
    letter-spacing: normal !important;
    white-space: nowrap !important;
    margin: 0 !important;
    padding: 0 !important;
}
.sb-brand-text .hz-accent {
    color: #F5A623 !important;
    margin: 0 !important;
    padding: 0 !important;
    display: inline !important;
}
.sb-logo {
    width: 28px;
    height: 28px;
    object-fit: contain;
    flex-shrink: 0;
}

/* Sidebar File Uploader (Collision-free layout) */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    width: 100% !important;
    margin-bottom: 0.6rem !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border: 1.5px dashed rgba(245, 166, 35, 0.4) !important;
    border-radius: 8px !important;
    padding: 0.75rem 0.5rem !important;
    width: 100% !important;
    text-align: center !important;
    min-height: auto !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
    border-color: #F5A623 !important;
    background-color: rgba(255, 255, 255, 0.08) !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 3px !important;
    padding: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] span {
    font-size: 0.78rem !important;
    color: #D1D5DB !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small {
    font-size: 0.68rem !important;
    color: #9CA3AF !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] button,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
    padding: 0.35rem 0.75rem !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    font-family: 'Outfit', sans-serif !important;
    border-radius: 6px !important;
    background: rgba(245, 166, 35, 0.15) !important;
    color: #F5A623 !important;
    border: 1px solid rgba(245, 166, 35, 0.4) !important;
    margin-top: 4px !important;
    min-height: auto !important;
    height: auto !important;
    box-shadow: none !important;
}

/* Uploaded file entry row */
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"],
[data-testid="stSidebar"] [data-testid="stUploadedFileData"],
[data-testid="stSidebar"] ul[data-testid="stFileUploaderFile"] {
    background: rgba(255, 255, 255, 0.07) !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    border-radius: 8px !important;
    padding: 7px 10px !important;
    margin-top: 8px !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 8px !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

[data-testid="stSidebar"] [data-testid="stUploadedFileData"] > div:first-child,
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] > div:first-child {
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
    min-width: 0 !important;
    flex: 1 1 auto !important;
}

[data-testid="stSidebar"] [data-testid="stUploadedFileData"] span,
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] span {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: #FFFFFF !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    display: block !important;
}

[data-testid="stSidebar"] [data-testid="stUploadedFileData"] small,
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] small {
    font-size: 0.68rem !important;
    color: #9CA3AF !important;
    display: block !important;
    margin-top: 1px !important;
}

/* Clear / Delete button inside file uploader */
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] button,
[data-testid="stSidebar"] [data-testid="stUploadedFileData"] button,
[data-testid="stSidebar"] [data-testid="stFileUploaderDeleteBtn"] {
    flex-shrink: 0 !important;
    width: 26px !important;
    height: 26px !important;
    min-height: 26px !important;
    padding: 0 !important;
    margin: 0 !important;
    background: rgba(239, 68, 68, 0.15) !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
    border-radius: 6px !important;
    color: #EF4444 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] button:hover,
[data-testid="stSidebar"] [data-testid="stUploadedFileData"] button:hover {
    background: rgba(239, 68, 68, 0.35) !important;
    color: #FFFFFF !important;
}

/* Sidebar Action Buttons (Start / Stop) */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="element-container"] .stButton > button {
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
    margin-bottom: 16px;
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
    white-space: nowrap;
}
.hz-title .hz-accent {
    color: #F5A623 !important;
    margin: 0 !important;
    padding: 0 !important;
    display: inline !important;
}
.hz-subtitle {
    color: #9CA3AF;
    font-size: 0.8rem;
    font-family: 'Plus Jakarta Sans', sans-serif;
    margin-top: 1px;
}

/* Status Pill & Real-time FPS Badge */
.hz-header-right {
    display: flex;
    align-items: center;
    gap: 8px;
}
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
.fps-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    background-color: rgba(245, 166, 35, 0.15);
    color: #F5A623;
    border: 1px solid rgba(245, 166, 35, 0.35);
    white-space: nowrap;
}
.pulse-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: #10B981;
}

/* Panel Headings: High-Contrast Dark Navy, Bold, ~1.3rem */
.panel-heading {
    font-family: 'Outfit', 'Plus Jakarta Sans', -apple-system, sans-serif !important;
    font-size: 1.3rem !important;
    font-weight: 700 !important;
    color: #1A1A2E !important;
    margin: 0 0 10px 0 !important;
    padding: 0 !important;
    line-height: 1.3 !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    letter-spacing: -0.01em !important;
}

.section-heading-2 {
    margin-top: 22px !important;
    margin-bottom: 10px !important;
}

/* Responsive Video Container */
.video-viewport {
    background: #0E0F17;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
    overflow: hidden;
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}
.video-viewport [data-testid="stImage"] img {
    border-radius: 8px;
    display: block;
    width: 100% !important;
    object-fit: contain;
}

/* Video Empty State */
.video-empty-box {
    background: #FFFFFF;
    border: 1.5px dashed #CBD5E1;
    border-radius: 12px;
    padding: 2.8rem 1.5rem;
    text-align: center;
    color: #64748B;
    width: 100%;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
}
.ve-icon {
    font-size: 2.5rem;
    display: block;
    margin-bottom: 0.4rem;
}
.ve-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #1A1A2E;
    margin-bottom: 0.25rem;
}
.ve-sub {
    font-size: 0.85rem;
    color: #64748B;
}

/* Statistics Grid: Responsive Equal Width & Height */
.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    width: 100%;
    margin-bottom: 0;
    align-items: stretch;
}
.stat-card {
    border-radius: 12px;
    padding: 14px 16px;
    box-sizing: border-box;
    width: 100%;
    min-height: 84px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    color: #FFFFFF;
    box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stat-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 5px 16px rgba(0, 0, 0, 0.12);
}
.stat-ppe {
    background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%);
    border: 1px solid rgba(220, 38, 38, 0.3);
}
.stat-zone {
    background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%);
    border: 1px solid rgba(234, 88, 12, 0.3);
}
.sc-label {
    font-family: 'Outfit', sans-serif;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.95);
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.sc-value {
    font-family: 'Outfit', sans-serif;
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1;
    color: #FFFFFF;
}

/* Site Safety Inspector Card Frame (Column 2) */
[data-testid="column"]:nth-of-type(2) [data-testid="stImage"] {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 8px;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}
[data-testid="column"]:nth-of-type(2) [data-testid="stImage"] img {
    border-radius: 8px;
    max-height: 225px;
    width: 100% !important;
    object-fit: cover;
}

/* Card Container Base */
.card-container {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
    overflow: hidden;
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
.card-container:hover {
    border-color: #D1D5DB;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.07);
}

/* Violation Log Table Container */
.violation-table-card {
    width: 100%;
}

.table-scroll-wrap {
    width: 100%;
    max-height: 270px;
    overflow-y: auto;
    overflow-x: auto;
}

/* Sleek custom scrollbar */
.table-scroll-wrap::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
.table-scroll-wrap::-webkit-scrollbar-track {
    background: #F8FAFC;
}
.table-scroll-wrap::-webkit-scrollbar-thumb {
    background: #CBD5E1;
    border-radius: 4px;
}
.table-scroll-wrap::-webkit-scrollbar-thumb:hover {
    background: #94A3B8;
}

/* Violation Table */
.violation-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.84rem;
}

.violation-table thead {
    position: sticky;
    top: 0;
    z-index: 5;
    background: #F8FAFC;
}

.v-th {
    padding: 10px 14px;
    font-family: 'Outfit', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #475569;
    border-bottom: 1px solid #E2E8F0;
    white-space: nowrap;
}
.v-th-time { width: 14%; min-width: 85px; }
.v-th-type { width: 26%; min-width: 150px; }
.v-th-conf { width: 15%; min-width: 95px; }
.v-th-details { width: 45%; min-width: 200px; }

.v-row {
    border-bottom: 1px solid #F1F5F9;
    transition: background-color 0.15s ease;
}
.v-row:nth-child(even) {
    background-color: #FAFAFB;
}
.v-row:hover {
    background-color: #F1F5F9 !important;
}

.v-cell {
    padding: 9px 14px;
    vertical-align: middle;
    color: #1E293B;
}
.v-cell-time {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    color: #475569;
    white-space: nowrap;
}
.v-cell-type {
    white-space: nowrap;
}
.v-cell-conf {
    white-space: nowrap;
}
.conf-pill {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    background: #F1F5F9;
    color: #334155;
    border: 1px solid #E2E8F0;
}
.v-cell-details {
    font-size: 0.82rem;
    line-height: 1.4;
    color: #1E293B;
    word-break: break-word;
}

/* Violation Badges */
.v-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 9px;
    border-radius: 20px;
    font-family: 'Outfit', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    white-space: nowrap;
}
.badge-intrusion {
    background-color: #FEF2F2;
    color: #991B1B;
    border: 1px solid #FECACA;
}
.badge-ppe {
    background-color: #FFFBEB;
    color: #92400E;
    border: 1px solid #FDE68A;
}
.badge-zone {
    background-color: #FFF7ED;
    color: #9A3412;
    border: 1px solid #FFEDD5;
}
.badge-default {
    background-color: #F3F4F6;
    color: #374151;
    border: 1px solid #E5E7EB;
}

.v-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}
.v-dot-red {
    background-color: #EF4444;
    box-shadow: 0 0 5px rgba(239, 68, 68, 0.6);
}
.v-dot-amber {
    background-color: #F59E0B;
    box-shadow: 0 0 5px rgba(245, 158, 11, 0.6);
}
.v-dot-orange {
    background-color: #F97316;
    box-shadow: 0 0 5px rgba(249, 115, 22, 0.6);
}

/* Empty log state */
.log-empty-card {
    padding: 1.8rem 1.2rem;
    text-align: center;
    background: #FFFFFF;
}
.log-empty-icon {
    font-size: 2rem;
    margin-bottom: 0.35rem;
}
.log-empty-title {
    font-family: 'Outfit', sans-serif;
    font-size: 0.98rem;
    font-weight: 700;
    color: #1A1A2E;
    margin-bottom: 0.25rem;
}
.log-empty-sub {
    font-size: 0.8rem;
    color: #64748B;
}

@media (max-width: 1024px) {
    .stats-grid {
        grid-template-columns: 1fr;
    }
}
</style>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Warm-up Models via Cache (Loads once in memory)
# ─────────────────────────────────────────────────────────────

DEVICE = get_optimal_device()
ppe_model_cached, person_model_cached = load_cached_yolo_models(
    PPE_WEIGHTS, PERSON_WEIGHTS, device=DEVICE
)


# ─────────────────────────────────────────────────────────────
# Main Header (Logo + Title + Status Pill)
# ─────────────────────────────────────────────────────────────

header_placeholder = st.empty()

def render_header(is_running: bool = False, display_fps: float = 0.0, ai_fps: float = 0.0):
    if is_running:
        if display_fps > 0 and ai_fps > 0:
            fps_tag = f'<span class="fps-pill" title="Display: {display_fps:.1f} FPS | AI Inference: {ai_fps:.1f} FPS">⚡ {display_fps:.1f} FPS <span style="opacity:0.75;font-size:0.68rem;font-weight:500;margin-left:3px;">(AI: {ai_fps:.1f})</span></span>'
        elif display_fps > 0:
            fps_tag = f'<span class="fps-pill">⚡ {display_fps:.1f} FPS</span>'
        else:
            fps_tag = ''
        status_html = f'{fps_tag}<span class="status-pill active"><span class="pulse-dot"></span> MONITORING ACTIVE</span>'
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
    header_placeholder.markdown(header_html, unsafe_allow_html=True)

render_header(st.session_state.get("running", False))


# ─────────────────────────────────────────────────────────────
# Sidebar (Single Clean File Uploader & Controls)
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    sb_logo_tag = f'<img src="{logo_b64}" class="sb-logo" alt="Logo" />' if logo_b64 else '🦺'
    st.markdown(
        f'<div class="sb-brand">{sb_logo_tag}<div class="sb-brand-text">Hazard<span class="hz-accent">Lens</span></div></div>',
        unsafe_allow_html=True
    )

    # 1. Video Source File Uploader
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
    zone_preset_name = st.selectbox(
        "🚧 Restricted Zone Area",
        list(ZONE_PRESETS.keys()),
        index=0,
    )
    selected_zone = ZONE_PRESETS.get(zone_preset_name, list(ZONE_PRESETS.values())[0])

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
# Left column (70%)  → Live Safety Monitoring + Violation Log
# Right column (30%) → Live Stats + Site Safety Inspector
# ─────────────────────────────────────────────────────────────

col_video, col_side = st.columns([2.3, 1.0])

with col_video:
    st.markdown('<div class="panel-heading">🎥 Live Safety Monitoring</div>', unsafe_allow_html=True)
    video_placeholder = st.empty()

    st.markdown('<div class="panel-heading section-heading-2">📋 Violation Log</div>', unsafe_allow_html=True)
    log_placeholder = st.empty()

with col_side:
    st.markdown('<div class="panel-heading">📊 Live Stats</div>', unsafe_allow_html=True)
    stats_placeholder = st.empty()

    st.markdown('<div class="panel-heading section-heading-2">👷 Site Safety Inspector</div>', unsafe_allow_html=True)
    if EXACT_AVATAR_PATH and os.path.exists(EXACT_AVATAR_PATH):
        st.image(EXACT_AVATAR_PATH, use_container_width=True)


def render_stat_cards(ppe_count: int, zone_count: int):
    """Render equal-width, equal-height statistics cards."""
    html_content = (
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
    stats_placeholder.markdown(html_content, unsafe_allow_html=True)


def render_log(violations: list):
    """Render real-time violation log table with zero empty trailing rows and status badges."""
    if not violations:
        empty_html = (
            '<div class="card-container log-empty-card">'
            '<div class="log-empty-icon">🛡️</div>'
            '<div class="log-empty-title">No Violations Detected</div>'
            '<div class="log-empty-sub">Active video stream will record unauthorized intrusions and PPE events here in real time.</div>'
            '</div>'
        )
        log_placeholder.markdown(empty_html, unsafe_allow_html=True)
        return

    display_data = violations[::-1][:50]
    rows_html = []

    for item in display_data:
        v_time = str(item.get("Time", "--:--:--"))
        v_type = str(item.get("Type", "UNKNOWN")).upper()
        v_conf = item.get("Confidence", "0.00")
        v_details = str(item.get("Details", ""))

        if "INTRUSION" in v_type:
            badge_html = '<span class="v-badge badge-intrusion"><span class="v-dot v-dot-red"></span>INTRUSION</span>'
        elif "PPE" in v_type:
            badge_html = '<span class="v-badge badge-ppe"><span class="v-dot v-dot-amber"></span>PPE VIOLATION</span>'
        elif "ZONE" in v_type:
            badge_html = '<span class="v-badge badge-zone"><span class="v-dot v-dot-orange"></span>ZONE BREACH</span>'
        else:
            badge_html = f'<span class="v-badge badge-default">{html.escape(v_type)}</span>'

        try:
            conf_float = float(v_conf)
            conf_display = f"{int(conf_float * 100)}%" if conf_float <= 1.0 else f"{conf_float:.0f}%"
        except Exception:
            conf_display = str(v_conf)

        safe_details = html.escape(v_details)
        safe_time = html.escape(v_time)
        safe_conf = html.escape(conf_display)

        row = (
            '<tr class="v-row">'
            f'<td class="v-cell v-cell-time">{safe_time}</td>'
            f'<td class="v-cell v-cell-type">{badge_html}</td>'
            f'<td class="v-cell v-cell-conf"><span class="conf-pill">{safe_conf}</span></td>'
            f'<td class="v-cell v-cell-details" title="{safe_details}">{safe_details}</td>'
            '</tr>'
        )
        rows_html.append(row)

    table_html = (
        '<div class="card-container violation-table-card">'
        '<div class="table-scroll-wrap">'
        '<table class="violation-table">'
        '<thead>'
        '<tr>'
        '<th class="v-th v-th-time">Time</th>'
        '<th class="v-th v-th-type">Type</th>'
        '<th class="v-th v-th-conf">Confidence</th>'
        '<th class="v-th v-th-details">Details</th>'
        '</tr>'
        '</thead>'
        '<tbody>'
        + ''.join(rows_html) +
        '</tbody>'
        '</table>'
        '</div>'
        '</div>'
    )
    log_placeholder.markdown(table_html, unsafe_allow_html=True)


# Initial render of stats and log
render_stat_cards(0, 0)
render_log(st.session_state.violations)


# ─────────────────────────────────────────────────────────────
# Decoupled ~40 FPS Continuous Video Monitoring Loop
# ─────────────────────────────────────────────────────────────

if st.session_state.running:
    render_header(True, 0.0, 0.0)

    # ── Load / Resolve video source (Write to disk once) ────────
    temp_path = "temp_uploaded_video.mp4"
    if uploaded_file is not None:
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) != uploaded_file.size:
            uploaded_file.seek(0)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
    elif os.path.exists(temp_path):
        pass
    elif os.path.exists("demo.mp4"):
        temp_path = "demo.mp4"
    else:
        st.warning("Please upload a video file in the sidebar to begin monitoring.")
        st.session_state.running = False
        render_header(False)
        st.stop()

    try:
        detector = SafeZoneDetector(
            ppe_weights=PPE_WEIGHTS,
            person_weights=PERSON_WEIGHTS,
            conf_threshold=conf_threshold,
            zone_coords=selected_zone,
            ppe_model=ppe_model_cached,
            person_model=person_model_cached,
            imgsz=INFERENCE_IMGSZ,
            device=DEVICE,
        )
        async_worker = AsyncInferenceWorker(detector)
    except Exception as e:
        st.error(f"Could not initialize detector: {e}")
        st.session_state.running = False
        render_header(False)
        st.stop()

    cap = cv2.VideoCapture(temp_path)
    if not cap.isOpened():
        st.error("Unable to open video stream. Please verify video format.")
        st.session_state.running = False
        render_header(False)
        st.stop()

    # Target 40 FPS display pacing (~25ms interval)
    target_display_fps = 40.0
    target_frame_interval = 1.0 / target_display_fps

    ppe_count = 0
    zone_count = 0
    last_rendered_counts = (-1, -1)
    last_log_count = -1

    fps_start_time = time.perf_counter()
    frames_displayed = 0
    current_display_fps = 0.0
    latest_ai_fps = 0.0
    last_header_fps_update = 0.0

    try:
        while cap.isOpened() and st.session_state.running:
            t_frame_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                break

            frames_displayed += 1

            # High-efficiency display scaling for rapid Streamlit WebSocket transfer
            h, w = frame.shape[:2]
            if w > MAX_PROCESSING_WIDTH:
                scale = MAX_PROCESSING_WIDTH / w
                frame = cv2.resize(frame, (MAX_PROCESSING_WIDTH, int(h * scale)), interpolation=cv2.INTER_LINEAR)

            # Submit frame to single-element buffer for background AI inference (non-blocking)
            async_worker.submit_frame(frame)

            # Retrieve latest AI annotations & new violation events (non-blocking, <0.01ms)
            ai_data, new_violations, ai_fps, avg_infer_time = async_worker.get_latest_result()
            if ai_fps > 0:
                latest_ai_fps = ai_fps

            if new_violations:
                for v in new_violations:
                    st.session_state.violations.append({
                        "Time": time.strftime("%H:%M:%S", time.localtime(v.timestamp)),
                        "Type": v.type,
                        "Confidence": f"{v.confidence:.2f}",
                        "Details": v.details,
                    })
                    if v.type == "INTRUSION":
                        zone_count += 1
                        ppe_count += 1
                    elif v.type == "PPE":
                        ppe_count += 1
                    elif v.type == "ZONE":
                        zone_count += 1

            # Fast <0.5ms OpenCV annotation using latest available detections
            annotated_frame = detector.annotate_frame(frame, ai_data)

            # Stream annotated frame directly to persistent placeholder
            rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)

            # Real measured Display FPS calculation (every 0.5s)
            now = time.perf_counter()
            elapsed = now - fps_start_time
            if elapsed >= 0.5:
                current_display_fps = frames_displayed / elapsed
                frames_displayed = 0
                fps_start_time = now

                if now - last_header_fps_update >= 0.6:
                    render_header(True, current_display_fps, latest_ai_fps)
                    last_header_fps_update = now

            # Performance: Only re-render stats cards when count numbers change
            if (ppe_count, zone_count) != last_rendered_counts:
                render_stat_cards(ppe_count, zone_count)
                last_rendered_counts = (ppe_count, zone_count)

            # Performance: Only re-render log table when new violation events arrive
            if len(st.session_state.violations) != last_log_count:
                render_log(st.session_state.violations)
                last_log_count = len(st.session_state.violations)

            # Precise ~40 FPS pacing (25ms total frame time)
            elapsed_frame = time.perf_counter() - t_frame_start
            if elapsed_frame < target_frame_interval:
                time.sleep(target_frame_interval - elapsed_frame)

    finally:
        async_worker.stop()
        cap.release()

    render_header(False)

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

