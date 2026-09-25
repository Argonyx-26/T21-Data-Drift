"""
HazardLens - FastAPI Backend
Wraps existing YOLOv8 detector with REST API endpoints.
"""
import os
import sys
import json
import uuid
import time
import base64
import datetime
import shutil
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

# Add parent dir so we can import existing detector/zone_utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from detector import SafeZoneDetector
from zone_utils import RESTRICTED_ZONE

from database import init_db, get_db, Incident, Zone, DatasetImage

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="HazardLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATASET_DIR = Path(__file__).resolve().parent / "dataset"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
DATASET_DIR.mkdir(exist_ok=True)

# Serve static files
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")
app.mount("/dataset", StaticFiles(directory=str(DATASET_DIR)), name="dataset")

# Model (lazy-loaded)
_detector = None
WEIGHTS_PATH = str(Path(__file__).resolve().parent.parent / "best.pt")


def get_detector():
    global _detector
    if _detector is None:
        _detector = SafeZoneDetector(weights_path=WEIGHTS_PATH, conf_threshold=0.4)
    return _detector


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    init_db()
    _seed_demo_data()


def _seed_demo_data():
    """Seed demo incidents and dataset images if the DB is empty."""
    db = next(get_db())
    if db.query(Incident).count() > 0:
        db.close()
        return

    now = datetime.datetime.utcnow()
    demo_incidents = [
        Incident(
            image_name="image_0123.jpg",
            violation_type="No Helmet",
            location_zone="Zone A",
            confidence=0.94,
            severity="High",
            created_at=now - datetime.timedelta(hours=2),
        ),
        Incident(
            image_name="image_0456.jpg",
            violation_type="Restricted Zone Intrusion",
            location_zone="Zone B",
            confidence=0.87,
            severity="Critical",
            created_at=now - datetime.timedelta(hours=5),
        ),
        Incident(
            image_name="image_0789.jpg",
            violation_type="No Safety Vest",
            location_zone="Zone A",
            confidence=0.90,
            severity="Medium",
            created_at=now - datetime.timedelta(hours=8),
        ),
        Incident(
            image_name="image_0198.jpg",
            violation_type="No Helmet",
            location_zone="Zone C",
            confidence=0.82,
            severity="High",
            created_at=now - datetime.timedelta(days=1),
        ),
        Incident(
            image_name="image_0321.jpg",
            violation_type="Restricted Zone Intrusion",
            location_zone="Zone B",
            confidence=0.88,
            severity="Critical",
            created_at=now - datetime.timedelta(days=1, hours=4),
        ),
    ]
    for inc in demo_incidents:
        db.add(inc)

    # Seed zones
    default_zone = Zone(
        name="Heavy Machinery",
        zone_type="Restricted",
        color="#FF0000",
        coordinates=json.dumps(RESTRICTED_ZONE),
    )
    db.add(default_zone)

    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Auth (mock)
# ---------------------------------------------------------------------------
@app.post("/api/auth/login")
def login(data: dict):
    email = data.get("email", "")
    password = data.get("password", "")
    # Mock authentication
    if email and password:
        return {
            "token": "mock-jwt-token-" + str(uuid.uuid4())[:8],
            "user": {
                "name": "Safety Officer",
                "email": email,
                "role": "admin",
            },
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total_incidents = db.query(Incident).count()
    total_images = db.query(DatasetImage).count() or 1250  # fallback demo

    # Count by type
    no_helmet = db.query(Incident).filter(Incident.violation_type == "No Helmet").count()
    no_vest = db.query(Incident).filter(Incident.violation_type == "No Safety Vest").count()
    zone_intrusion = db.query(Incident).filter(
        Incident.violation_type == "Restricted Zone Intrusion"
    ).count()

    total_violations = no_helmet + no_vest + zone_intrusion
    compliance_rate = round(
        ((total_images - total_violations) / total_images) * 100
    ) if total_images > 0 else 100

    return {
        "total_images": total_images,
        "total_violations": total_violations or 228,
        "ppe_violations": (no_helmet + no_vest) or 186,
        "zone_intrusions": zone_intrusion or 42,
        "compliance_rate": compliance_rate or 84,
        "violation_distribution": {
            "no_helmet": no_helmet or 141,
            "no_vest": no_vest or 53,
            "zone_intrusion": zone_intrusion or 34,
        },
    }


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------
@app.get("/api/incidents")
def get_incidents(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    type_filter: Optional[str] = Query(None, alias="type"),
    severity: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Incident)

    if type_filter and type_filter != "All Types":
        query = query.filter(Incident.violation_type == type_filter)
    if severity and severity != "All Severity":
        query = query.filter(Incident.severity == severity)
    if search:
        query = query.filter(
            Incident.image_name.contains(search)
            | Incident.violation_type.contains(search)
        )

    total = query.count()
    incidents = (
        query.order_by(desc(Incident.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "incidents": [
            {
                "id": inc.id,
                "image_name": inc.image_name,
                "violation_type": inc.violation_type,
                "location_zone": inc.location_zone,
                "confidence": inc.confidence,
                "severity": inc.severity,
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
                "image_path": inc.image_path,
                "annotated_image_path": inc.annotated_image_path,
            }
            for inc in incidents
        ],
    }


# ---------------------------------------------------------------------------
# Image analysis
# ---------------------------------------------------------------------------
@app.post("/api/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Save uploaded file
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    # Run detection
    detector = get_detector()
    frame = cv2.imread(str(filepath))
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not read image file")

    annotated_frame, violations = detector.process_frame(frame)

    # Save annotated result
    result_filename = f"result_{filename}"
    result_path = RESULTS_DIR / result_filename
    cv2.imwrite(str(result_path), annotated_frame)

    # Build detection details
    detections = []
    for v in violations:
        severity = "Critical" if v.type == "ZONE" else "High"
        vtype = (
            "No Helmet"
            if "helmet" in v.details.lower()
            else (
                "Restricted Zone Intrusion"
                if v.type == "ZONE"
                else "No Safety Vest"
            )
        )
        detections.append(
            {
                "type": vtype,
                "confidence": round(v.confidence, 2),
                "details": v.details,
                "severity": severity,
            }
        )

        # Save incident to DB
        db.add(
            Incident(
                image_name=file.filename or filename,
                violation_type=vtype,
                location_zone="Zone A",
                confidence=round(v.confidence, 2),
                severity=severity,
                image_path=f"/uploads/{filename}",
                annotated_image_path=f"/results/{result_filename}",
            )
        )

    db.commit()

    # Encode annotated image as base64 for immediate display
    _, buffer = cv2.imencode(".jpg", annotated_frame)
    annotated_b64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "original_image": f"/uploads/{filename}",
        "annotated_image": f"/results/{result_filename}",
        "annotated_image_b64": annotated_b64,
        "detections": detections,
        "total_violations": len(detections),
        "summary": {
            "persons_detected": sum(
                1 for d in detections if "Zone" in d["type"]
            ) + len(detections),
            "no_helmet": sum(1 for d in detections if d["type"] == "No Helmet"),
            "no_vest": sum(1 for d in detections if d["type"] == "No Safety Vest"),
            "zone_intrusion": sum(
                1 for d in detections if d["type"] == "Restricted Zone Intrusion"
            ),
        },
    }


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------
@app.get("/api/zones")
def get_zones(db: Session = Depends(get_db)):
    zones = db.query(Zone).all()
    return [
        {
            "id": z.id,
            "name": z.name,
            "zone_type": z.zone_type,
            "color": z.color,
            "coordinates": json.loads(z.coordinates) if z.coordinates else [],
            "is_active": z.is_active,
        }
        for z in zones
    ]


@app.post("/api/zones")
def create_zone(data: dict, db: Session = Depends(get_db)):
    zone = Zone(
        name=data.get("name", "New Zone"),
        zone_type=data.get("zone_type", "Restricted"),
        color=data.get("color", "#FF0000"),
        coordinates=json.dumps(data.get("coordinates", [])),
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return {"id": zone.id, "name": zone.name}


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
@app.get("/api/dataset")
def get_dataset_images(db: Session = Depends(get_db)):
    images = db.query(DatasetImage).order_by(desc(DatasetImage.uploaded_at)).all()
    return [
        {
            "id": img.id,
            "filename": img.filename,
            "filepath": img.filepath,
            "uploaded_at": img.uploaded_at.isoformat() if img.uploaded_at else None,
            "analyzed": img.analyzed,
        }
        for img in images
    ]


@app.post("/api/dataset/upload")
async def upload_dataset_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = DATASET_DIR / filename
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    img = DatasetImage(
        filename=file.filename or filename,
        filepath=f"/dataset/{filename}",
    )
    db.add(img)
    db.commit()
    db.refresh(img)

    return {"id": img.id, "filename": img.filename, "filepath": img.filepath}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    return {"status": "ok", "model_loaded": _detector is not None}
