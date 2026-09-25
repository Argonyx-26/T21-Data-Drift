# 🦺 HazardLens

> **AI-Powered Workplace Safety Monitoring using Computer Vision**

HazardLens is a computer-vision-based workplace safety monitoring system
designed to identify **helmet/PPE non-compliance** and **unauthorized
entry into restricted work zones** from uploaded images or video.

The project combines a custom-trained **YOLOv8 PPE model**, a pretrained
**YOLOv8 person detector**, geometric restricted-zone analysis, object
tracking, event deduplication, a FastAPI backend, SQLite persistence,
and a Next.js dashboard.

The system is designed around a simple safety question:

> **Is a worker in a restricted work area, and if so, are they wearing
> the required helmet/PPE?**

------------------------------------------------------------------------

## 📌 Table of Contents

-   [1. Project Overview](#1-project-overview)
-   [2. Problem Statement](#2-problem-statement)
-   [3. Solution](#3-solution)
-   [4. Key Features](#4-key-features)
-   [5. System Architecture](#5-system-architecture)
-   [6. Detection Pipeline](#6-detection-pipeline)
-   [7. PPE Detection](#7-ppe-detection)
-   [8. Person Detection and Recall
    Recovery](#8-person-detection-and-recall-recovery)
-   [9. Restricted-Zone Detection](#9-restricted-zone-detection)
-   [10. Intrusion Decision Logic](#10-intrusion-decision-logic)
-   [11. Confidence Threshold](#11-confidence-threshold)
-   [12. Tracking and Event
    Deduplication](#12-tracking-and-event-deduplication)
-   [13. Model Training](#13-model-training)
-   [14. Model Evaluation](#14-model-evaluation)
-   [15. Backend](#15-backend)
-   [16. Database](#16-database)
-   [17. Frontend](#17-frontend)
-   [18. Project Structure](#18-project-structure)
-   [19. Installation](#19-installation)
-   [20. Running HazardLens](#20-running-hazardlens)
-   [21. Zone Calibration](#21-zone-calibration)
-   [22. API Endpoints](#22-api-endpoints)
-   [23. Example Workflow](#23-example-workflow)
-   [24. Technology Stack](#24-technology-stack)
-   [25. Current Limitations](#25-current-limitations)
-   [26. Future Improvements](#26-future-improvements)
-   [27. Team/Project Presentation
    Summary](#27-teamproject-presentation-summary)
-   [28. License](#28-license)

------------------------------------------------------------------------

# 1. Project Overview

HazardLens is a workplace-safety computer vision platform that analyzes
visual data and identifies situations that may require safety
intervention.

The current core detection system focuses on:

1.  **Head detection**
2.  **Helmet detection**
3.  **Person detection**
4.  **Restricted-zone detection**
5.  **Helmet/PPE compliance**
6.  **Restricted-zone intrusion detection**
7.  **Violation event logging**

The project has two application layers:

### Streamlit monitoring application

The original/standalone monitoring interface is implemented in `app.py`.

It can:

-   accept an uploaded video
-   process frames sequentially
-   run the detection pipeline
-   draw detections and the restricted zone
-   display live statistics
-   show detected violation events

### Full-stack web application

The project also contains:

-   a **FastAPI backend**
-   a **SQLite database**
-   a **Next.js frontend**

The frontend provides dashboard-style pages for analysis, incidents,
zones, analytics, settings, and authentication.

------------------------------------------------------------------------

# 2. Problem Statement

Workplace accidents can occur when workers:

-   enter hazardous or restricted areas without authorization
-   fail to wear required protective equipment
-   work in areas where safety rules are being violated

Traditional monitoring can depend heavily on manual observation.

HazardLens explores an automated approach where computer vision
continuously analyzes visual input and converts detections into
understandable safety events.

For example:

``` text
Worker detected
      ↓
Helmet detected?
      ↓
Where is the worker?
      ↓
Inside restricted zone?
      ↓
 ┌───────────────┐
 │               │
YES             NO
 │               │
Helmet?         Helmet?
 │               │
 ├─ YES → Safe   ├─ YES → Safe
 └─ NO  →        └─ NO  → PPE violation
         Intrusion
```

------------------------------------------------------------------------

# 3. Solution

HazardLens uses a **dual-model detection architecture**.

### Model 1 --- Custom PPE model

`best.pt`

The custom YOLOv8 model is trained on the Hard Hat Workers dataset and
is intended to detect:

-   `head`
-   `helmet`
-   `person`

The current runtime architecture primarily uses this model for **head
and helmet detection**.

### Model 2 --- Pretrained person model

`yolov8n.pt`

The pretrained YOLOv8 nano model is used to provide a separate
person-detection signal.

This was introduced because the original custom model showed weak
performance for the `person` class during evaluation.

### Why two models?

The project separates the responsibilities:

``` text
best.pt
 ├── Head
 └── Helmet

yolov8n.pt
 └── Person

        ↓

Combined detection pipeline
        ↓

Zone + PPE reasoning
        ↓

Safety event
```

This allows the system to retain the strong custom PPE detections while
using an independent person detector for worker localization.

------------------------------------------------------------------------

# 4. Key Features

## 🪖 Helmet/PPE Detection

HazardLens checks whether detected workers appear to have a helmet.

The system associates detected heads/helmets with detected person
regions.

------------------------------------------------------------------------

## 🚧 Restricted-Zone Detection

A polygon represents a restricted work area.

The system checks whether a detected person is inside or sufficiently
intersects that polygon.

------------------------------------------------------------------------

## 📐 Resolution-Independent Zones

Zone coordinates are stored in normalized form:

``` text
0.0 → 1.0
```

instead of fixed pixel coordinates.

Therefore the same zone definition can be converted to pixels for
different frame sizes such as:

``` text
1280 × 720
1920 × 1080
2560 × 1440
3840 × 2160
```

------------------------------------------------------------------------

## 👤 High-Recall Person Pipeline

The detection system uses multiple sources of person evidence:

-   person detections from the custom model
-   person detections from `yolov8n.pt`
-   proxy person boxes generated from detected heads/helmets when a body
    detection is missing

The candidates are then passed through NMS to reduce duplicate
detections.

------------------------------------------------------------------------

## 🎯 Tracking

Both YOLO pipelines use:

``` text
ByteTrack
```

through Ultralytics tracking with persistent tracking enabled.

Tracking provides object identities across consecutive frames and helps
the application reason about events rather than treating every frame as
a completely new detection.

------------------------------------------------------------------------

## 🔔 Event Deduplication

A continuous violation should not generate hundreds of separate
incidents simply because it remains visible for hundreds of frames.

HazardLens therefore maintains state for previously observed violation
tracks and generates discrete events.

------------------------------------------------------------------------

## 🖥️ Dashboard

The Streamlit application provides:

-   video upload
-   confidence control
-   monitoring controls
-   annotated video
-   PPE violation count
-   zone intrusion count
-   violation log

The Next.js frontend provides a broader dashboard experience with:

-   login
-   dashboard
-   image analysis
-   incidents
-   zones
-   analytics
-   settings
-   API health status

------------------------------------------------------------------------

# 5. System Architecture

The overall project can be understood as follows:

``` text
                         ┌──────────────────────┐
                         │      User Input      │
                         │ Image / Video Upload │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
                    ▼                                ▼
          ┌──────────────────┐             ┌──────────────────┐
          │ Streamlit App    │             │ Next.js Frontend │
          │     app.py       │             │     frontend/    │
          └────────┬─────────┘             └────────┬─────────┘
                   │                                │
                   │                                ▼
                   │                       ┌──────────────────┐
                   │                       │  FastAPI Backend │
                   │                       │    backend/      │
                   │                       └────────┬─────────┘
                   │                                │
                   └──────────────┬─────────────────┘
                                  ▼
                       ┌────────────────────┐
                       │ Detection Engine   │
                       │    detector.py     │
                       └─────────┬──────────┘
                                 │
                 ┌───────────────┼────────────────┐
                 │               │                │
                 ▼               ▼                ▼
            best.pt         yolov8n.pt       Zone Geometry
          Head/Helmet         Person        zone_utils.py
                 │               │                │
                 └───────────────┼────────────────┘
                                 ▼
                       ┌────────────────────┐
                       │ Safety Reasoning   │
                       │ PPE + Zone Logic   │
                       └─────────┬──────────┘
                                 ▼
                       ┌────────────────────┐
                       │ Violation Events   │
                       └─────────┬──────────┘
                                 ▼
                       ┌────────────────────┐
                       │ SQLite Database    │
                       │ hazardlens.db      │
                       └────────────────────┘
```

------------------------------------------------------------------------

# 6. Detection Pipeline

For each video/image frame, HazardLens performs the following process.

## Step 1 --- Read the frame

OpenCV obtains the current image frame.

## Step 2 --- Run PPE model

`best.pt` is executed using Ultralytics YOLO tracking.

The system extracts:

-   head boxes
-   helmet boxes
-   person boxes, when present

## Step 3 --- Run person model

`yolov8n.pt` is executed for class `person`.

A lower threshold is used to increase sensitivity.

## Step 4 --- Build candidate persons

Person candidates from both models are combined.

## Step 5 --- Recover missing persons

If a head or helmet is detected but no person box contains that
head/helmet, HazardLens can create a proxy person box.

## Step 6 --- Apply NMS

Overlapping candidate person boxes are filtered to reduce duplicate
detections.

## Step 7 --- Check restricted zone

Each final person candidate is tested against the configured polygon.

## Step 8 --- Check helmet status

The system checks whether a helmet overlaps the person's detected head
region.

## Step 9 --- Apply safety rules

The location and PPE state determine the final status.

## Step 10 --- Generate new events

Only new violation events are emitted to the application.

------------------------------------------------------------------------

# 7. PPE Detection

The custom model is trained around three classes:

``` text
head
helmet
person
```

The main PPE relationship is:

``` text
Head detected
       +
Helmet sufficiently overlaps head
       ↓
Helmet OK
```

If a head/person is detected without an associated helmet:

``` text
No helmet
   ↓
PPE violation
```

The detector uses bounding-box overlap logic rather than simply checking
whether any helmet exists somewhere in the frame.

This is important because a helmet belonging to one worker should not
automatically mark every other worker as compliant.

------------------------------------------------------------------------

# 8. Person Detection and Recall Recovery

The original custom model evaluation showed a major weakness in the
`person` class.

Previously measured test results were approximately:

``` text
Person precision : 100%
Person recall    : 0%
Person mAP50     : 4.05%
```

This means the custom model's person class could produce highly precise
detections when it detected a person, but it missed the vast majority of
annotated persons in the evaluation set.

Because restricted-zone monitoring depends heavily on person
localization, HazardLens adds a separate person pipeline.

## 8.1 Pretrained person detector

`yolov8n.pt` is run with:

``` text
classes = [0]
```

because class `0` in the COCO model represents a person.

The runtime person threshold is capped around:

``` text
0.25
```

to favor recall.

------------------------------------------------------------------------

## 8.2 Head/helmet proxy recovery

Construction workers can be partially hidden by:

-   scaffolding
-   equipment
-   barriers
-   camera framing
-   other workers

Sometimes the visible head/helmet is detectable even when the complete
body is not.

HazardLens uses this information to create a proxy person box.

Conceptually:

``` text
        HEAD / HELMET
             ↓
      ┌────────────┐
      │            │
      │   HEAD     │
      │            │
      │            │
      │   PROXY    │
      │   BODY     │
      │            │
      └────────────┘
```

The current implementation estimates the body region from the headwear
dimensions.

This is a **recovery heuristic**, not a separately trained person
detector.

------------------------------------------------------------------------

## 8.3 NMS

The candidate list can contain multiple boxes for the same worker.

Candidates can originate from:

``` text
best.pt
yolov8n.pt
head proxy
helmet proxy
```

Non-Maximum Suppression is applied to reduce strongly overlapping
duplicates.

------------------------------------------------------------------------

## 8.4 Important evaluation note

The original `best.pt` person recall metric does **not** represent the
recall of the complete HazardLens pipeline.

The new pipeline combines:

-   a second model
-   tracking
-   proxy recovery
-   NMS
-   zone reasoning

Therefore, any claim about the new system's person recall should be
supported by a new **system-level evaluation**.

The architecture is designed to improve person recall, but a new
measured recall percentage should only be reported after evaluating the
complete pipeline.

------------------------------------------------------------------------

# 9. Restricted-Zone Detection

A restricted zone is represented as a polygon.

For example:

``` text
       ┌─────────────────────────┐
       │                         │
       │       RESTRICTED        │
       │          ZONE           │
       │                         │
       └─────────────────────────┘
```

The polygon is stored using normalized coordinates.

Example:

``` python
[
    (0.08, 0.05),
    (0.92, 0.05),
    (0.92, 0.98),
    (0.08, 0.98),
]
```

The values represent proportions of:

``` text
x / frame width
y / frame height
```

The coordinates are converted to pixel coordinates for the current
frame.

------------------------------------------------------------------------

## 9.1 Why normalized coordinates?

A fixed pixel polygon would work only for a specific video resolution.

For example:

``` text
1920 × 1080
```

and:

``` text
1280 × 720
```

have different pixel coordinate systems.

Normalized coordinates solve this by defining the zone relative to the
frame.

------------------------------------------------------------------------

## 9.2 Multi-point zone checking

HazardLens does not rely only on the person's feet.

The current `is_person_in_zone()` logic checks:

### 1. Bottom-center

Approximates the person's foot position.

### 2. Bounding-box center

Useful when the lower body is not visible.

### 3. Bounding-box intersection

Calculates the overlap between the person box and the restricted
polygon.

The current implementation considers the person inside when the
intersection exceeds approximately:

``` text
15% of the person's bounding-box area
```

This makes the system less dependent on having a perfectly visible pair
of feet.

------------------------------------------------------------------------

# 10. Intrusion Decision Logic

The core safety logic is:

  Worker Location           Helmet   Result
  ------------------------- -------- -------------------
  Inside restricted zone    Yes      Authorized / safe
  Inside restricted zone    No       **Intrusion**
  Outside restricted zone   Yes      Normal
  Outside restricted zone   No       **PPE violation**

This distinction is important.

A person being inside a restricted zone is **not automatically
considered an intrusion** in the current logic.

The current rule is:

> **Restricted-zone entry without the required helmet is classified as
> an intrusion.**

Therefore:

``` text
Inside + Helmet
      ↓
AUTHORIZED
```

while:

``` text
Inside + No Helmet
      ↓
INTRUSION
```

Outside the zone:

``` text
Outside + No Helmet
      ↓
PPE VIOLATION
```

------------------------------------------------------------------------

# 11. Confidence Threshold

The confidence threshold is a filtering mechanism.

If YOLO produces:

``` text
Helmet → 0.92
Helmet → 0.73
Helmet → 0.21
```

and the threshold is:

``` text
0.40
```

then:

``` text
0.92 → accepted
0.73 → accepted
0.21 → ignored
```

The Streamlit application exposes a confidence control.

However, the detector intentionally uses bounded thresholds internally:

``` text
PPE threshold    ≈ 0.20–0.35
Person threshold ≈ 0.20–0.25
```

This prevents increasing the UI threshold from becoming overly
aggressive for the PPE/person sub-pipelines.

### Why use confidence?

The threshold helps balance:

``` text
Lower threshold
→ more detections
→ potentially higher recall
→ potentially more false positives

Higher threshold
→ fewer detections
→ potentially fewer false positives
→ potentially more missed objects
```

Confidence threshold is therefore **not the same thing as model
accuracy**.

------------------------------------------------------------------------

# 12. Tracking and Event Deduplication

A video contains many frames.

Suppose a worker without a helmet remains visible for 5 seconds at 30
FPS.

Without event handling, the same violation could be reported roughly:

``` text
5 × 30 = 150 frames
```

as separate events.

That would make the dashboard misleading.

HazardLens uses persistent tracking and event state to turn continuous
detections into discrete events.

The detector maintains sets/dictionaries such as:

``` python
_intrusion_seen
_intrusion_clean
_ppe_seen
_ppe_clean
```

and uses tracked IDs where available.

This means the system attempts to report:

``` text
Worker #12
    ↓
No helmet
    ↓
ONE PPE event
```

rather than:

``` text
Frame 1 → PPE
Frame 2 → PPE
Frame 3 → PPE
...
Frame 150 → PPE
```

------------------------------------------------------------------------

# 13. Model Training

The training script is `train.py`.

The project uses:

``` text
YOLOv8 Nano
```

as the starting model.

The training dataset is expected to contain:

``` text
head
helmet
person
```

The training configuration currently uses:

``` text
Epochs : 30
Image size : 640
Batch size : 16
Patience : 10
```

The training script attempts to use Apple Silicon MPS when available and
otherwise falls back to CPU.

Example:

``` bash
python train.py
```

The resulting best weights are expected under the training run directory
and can then be copied to:

``` text
Hazardlens/best.pt
```

------------------------------------------------------------------------

# 14. Model Evaluation

The previously measured evaluation results for the custom model were:

## Validation

  Class       Precision   Recall   mAP50   mAP50-95
  --------- ----------- -------- ------- ----------
  Head            0.931    0.927   0.961      0.666
  Helmet          0.966    0.935   0.982      0.681
  Person          1.000    0.000   0.029      0.015
  Overall         0.960    0.621   0.658      0.454

## Test

  Class       Precision   Recall    mAP50   mAP50-95
  --------- ----------- -------- -------- ----------
  Head            0.946    0.933    0.968      0.673
  Helmet          0.953    0.946    0.983      0.684
  Person          1.000    0.000   0.0405     0.0211
  Overall         0.966    0.626    0.664      0.460

### Interpretation

The custom model showed strong performance for:

-   head detection
-   helmet detection

The `person` class was the major weakness.

This is one of the reasons the deployed architecture uses:

``` text
best.pt + yolov8n.pt + proxy recovery
```

instead of relying solely on the custom model's person class.

### Important terminology

Do not describe:

``` text
Precision = 96.6%
```

as:

``` text
Accuracy = 96.6%
```

Precision, recall, mAP50, and mAP50-95 are different evaluation metrics.

------------------------------------------------------------------------

# 15. Backend

The backend is implemented using **FastAPI**.

Main files:

``` text
backend/
├── main.py
├── database.py
├── requirements.txt
├── hazardlens.db
├── uploads/
├── results/
└── dataset/
```

The backend wraps the existing detection engine and exposes REST APIs
for the frontend.

The detector is loaded lazily so that the model is initialized when the
application needs it.

------------------------------------------------------------------------

# 16. Database

HazardLens uses **SQLite** through SQLAlchemy.

The database is:

``` text
backend/hazardlens.db
```

The main database entities are:

## Incident

Stores safety events such as:

-   No Helmet
-   No Safety Vest
-   Restricted Zone Intrusion

Fields include:

``` text
id
image_name
violation_type
location_zone
confidence
severity
created_at
image_path
annotated_image_path
```

## Zone

Stores configured zones:

``` text
id
name
zone_type
color
coordinates
is_active
created_at
```

## DatasetImage

Stores uploaded dataset images:

``` text
id
filename
filepath
uploaded_at
analyzed
```

------------------------------------------------------------------------

# 17. Frontend

The frontend is implemented with:

-   Next.js
-   React
-   TypeScript
-   Recharts
-   Lucide React

It is located in:

``` text
frontend/
```

The main application areas include:

``` text
/
├── Login
│
└── Dashboard
    ├── Overview
    ├── Analyze
    ├── Incidents
    ├── Zones
    ├── Analytics
    └── Settings
```

The frontend communicates with the FastAPI backend using endpoints such
as:

``` text
/api/auth/login
/api/health
/api/stats
/api/incidents
/api/analyze
/api/zones
/api/dataset
/api/dataset/upload
```

------------------------------------------------------------------------

# 18. Project Structure

``` text
Hazardlens/
│
├── app.py
├── detector.py
├── zone_utils.py
├── train.py
│
├── best.pt
├── yolov8n.pt
├── requirements.txt
├── .gitignore
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── requirements.txt
│   ├── hazardlens.db
│   ├── uploads/
│   ├── results/
│   └── dataset/
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── next.config.js
│   ├── tsconfig.json
│   │
│   └── src/
│       ├── app/
│       │   ├── dashboard/
│       │   │   ├── analytics/
│       │   │   ├── analyze/
│       │   │   ├── incidents/
│       │   │   ├── settings/
│       │   │   └── zones/
│       │   └── page.tsx
│       │
│       └── components/
│
└── README.md
```

------------------------------------------------------------------------

# 19. Installation

## Prerequisites

Recommended:

-   Python 3.10--3.12
-   Node.js
-   npm
-   Git
-   macOS, Linux, or Windows
-   Optional GPU/MPS support for faster model execution

------------------------------------------------------------------------

## Python environment

From the `Hazardlens` directory:

``` bash
python3 -m venv venv
```

Activate it:

### macOS/Linux

``` bash
source venv/bin/activate
```

### Windows

``` powershell
venv\Scripts\activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

# 20. Running HazardLens

There are currently two application paths.

## Option A --- Streamlit monitoring application

From:

``` text
Hazardlens/
```

run:

``` bash
streamlit run app.py
```

Then open:

``` text
http://localhost:8501
```

The workflow is:

``` text
Upload video
      ↓
Choose confidence
      ↓
Start monitoring
      ↓
Frames processed
      ↓
YOLO detections
      ↓
PPE + zone reasoning
      ↓
Annotated output
      ↓
Violation events
```

------------------------------------------------------------------------

## Option B --- FastAPI + Next.js application

### Start backend

``` bash
cd backend
pip install -r requirements.txt
python main.py
```

The backend exposes the API used by the frontend.

### Start frontend

Open another terminal:

``` bash
cd frontend
npm install
npm run dev
```

Then open the local Next.js development URL shown by the terminal.

------------------------------------------------------------------------

# 21. Zone Calibration

The project includes an interactive calibration utility in:

``` text
zone_utils.py
```

Run:

``` bash
python zone_utils.py path/to/video.mp4
```

The tool opens the first frame.

### Controls

``` text
Left click  → add polygon point
Right click → close polygon
q           → finish
```

The tool prints normalized coordinates.

These coordinates can be used as the restricted zone definition.

------------------------------------------------------------------------

## Built-in presets

The current implementation contains:

### Active Work Site

``` text
(0.08, 0.05)
(0.92, 0.05)
(0.92, 0.98)
(0.08, 0.98)
```

### Center & Right Work Area

``` text
(0.30, 0.08)
(0.95, 0.08)
(0.95, 0.98)
(0.30, 0.98)
```

### Entire Frame

``` text
(0.01, 0.01)
(0.99, 0.01)
(0.99, 0.99)
(0.01, 0.99)
```

For real deployments, the zone should be calibrated to the actual camera
view rather than relying blindly on a generic preset.

------------------------------------------------------------------------

# 22. API Endpoints

## Authentication

### `POST /api/auth/login`

Accepts email and password and returns a mock authentication response.

> Current implementation uses mock authentication; it should not be
> treated as production-grade authentication.

------------------------------------------------------------------------

## Health

### `GET /api/health`

Returns backend health and model-loaded state.

Example:

``` json
{
  "status": "ok",
  "model_loaded": true
}
```

------------------------------------------------------------------------

## Statistics

### `GET /api/stats`

Returns dashboard-level incident statistics.

------------------------------------------------------------------------

## Incidents

### `GET /api/incidents`

Supports:

-   pagination
-   violation type filtering
-   severity filtering
-   search

Example:

``` text
/api/incidents?limit=10
```

------------------------------------------------------------------------

## Image Analysis

### `POST /api/analyze`

Uploads an image, runs the detection pipeline, saves an annotated
result, stores generated incidents, and returns detection information.

------------------------------------------------------------------------

## Zones

### `GET /api/zones`

Returns configured zones.

### `POST /api/zones`

Creates a new zone.

------------------------------------------------------------------------

## Dataset

### `GET /api/dataset`

Returns uploaded dataset images.

### `POST /api/dataset/upload`

Uploads a dataset image.

------------------------------------------------------------------------

# 23. Example Workflow

Consider a construction worker.

## Scenario A --- Helmet outside zone

``` text
Person detected
       ↓
Outside restricted zone
       ↓
Helmet detected
       ↓
SAFE
```

------------------------------------------------------------------------

## Scenario B --- No helmet outside zone

``` text
Person detected
       ↓
Outside restricted zone
       ↓
No helmet
       ↓
PPE VIOLATION
```

------------------------------------------------------------------------

## Scenario C --- Helmet inside restricted zone

``` text
Person detected
       ↓
Inside restricted zone
       ↓
Helmet detected
       ↓
AUTHORIZED
```

------------------------------------------------------------------------

## Scenario D --- No helmet inside restricted zone

``` text
Person detected
       ↓
Inside restricted zone
       ↓
No helmet
       ↓
🚨 INTRUSION
```

This is the primary combined safety event that HazardLens is designed to
surface.

------------------------------------------------------------------------

# 24. Technology Stack

  Layer                    Technology
  ------------------------ -------------------------------
  Computer Vision          YOLOv8 / Ultralytics
  Custom Model             `best.pt`
  Person Model             `yolov8n.pt`
  Object Tracking          ByteTrack
  Image/Video Processing   OpenCV
  Geometry                 Shapely
  ML Training              PyTorch + Ultralytics
  Standalone UI            Streamlit
  Backend                  FastAPI
  Database                 SQLite
  ORM                      SQLAlchemy
  Frontend                 Next.js
  Frontend Language        TypeScript
  UI/Charts                React, Recharts, Lucide React
  Data Processing          NumPy, Pandas

------------------------------------------------------------------------

# 25. Current Limitations

HazardLens is currently a project/research prototype rather than a
production-certified safety system.

## 25.1 Person-class weakness in the custom model

The original custom model's person class had:

``` text
Recall = 0%
```

in the measured test evaluation.

The runtime architecture addresses this with a separate person detector
and head/helmet proxy recovery, but the complete pipeline needs a
dedicated system-level recall evaluation.

------------------------------------------------------------------------

## 25.2 Proxy-person detection is heuristic

The head/helmet-to-person recovery creates an estimated body box.

It is useful for recovering partially visible workers, but it is not
equivalent to a true human-body detection.

------------------------------------------------------------------------

## 25.3 Zone configuration is camera-dependent

Normalized coordinates make zones resolution-independent, but they do
not make them viewpoint-independent.

If the camera moves substantially, the zone should be recalibrated.

------------------------------------------------------------------------

## 25.4 PPE scope

The current core detector is primarily focused on **helmet/head
compliance**.

The backend data model contains `"No Safety Vest"` as a supported
incident type, but the current detector logic shown in this repository
does not implement a dedicated safety-vest detector.

Therefore, a safety-vest detection capability should not be considered
equivalent to the current helmet detector without adding and evaluating
an appropriate model.

------------------------------------------------------------------------

## 25.5 Authentication is currently mocked

The login endpoint accepts a non-empty email/password and returns a mock
token.

It is suitable for demonstrating the frontend flow but is not a
production authentication system.

------------------------------------------------------------------------

## 25.6 Demo/fallback dashboard data

Some backend dashboard responses contain fallback/demo values when the
database does not contain corresponding records.

Therefore, dashboard numbers should be interpreted carefully when
demonstrating the prototype.

------------------------------------------------------------------------

## 25.7 Video processing architecture

The Streamlit application processes uploaded videos sequentially.

This is different from a production distributed video-monitoring
architecture with:

-   camera streams
-   message queues
-   GPU workers
-   alert services
-   centralized event processing

------------------------------------------------------------------------

# 26. Future Improvements

Potential future improvements include:

## Model improvements

-   retrain the person class with better annotations
-   expand the training dataset
-   add more difficult occlusion examples
-   evaluate additional YOLO model sizes
-   add explicit PPE classes such as safety vest, gloves, goggles, and
    boots
-   perform systematic threshold optimization

## Tracking improvements

-   stronger identity association
-   track persistence across occlusion
-   track-based violation duration
-   entry/exit event classification

## Zone improvements

-   draw zones directly in the web interface
-   save camera-specific zone configurations
-   support multiple simultaneous zones
-   support zone entry and zone exit events
-   add zone schedules and activation states

## Backend improvements

-   replace mock authentication with real authentication
-   add proper authorization and user roles
-   use PostgreSQL for larger deployments
-   add background processing for long videos
-   add WebSocket/SSE updates for live events

## Frontend improvements

-   real-time incident notifications
-   incident detail pages
-   annotated-frame preview
-   video timeline
-   event filtering
-   downloadable reports
-   configurable safety policies

## Evaluation improvements

A proper end-to-end evaluation should measure:

``` text
Person Precision
Person Recall
Helmet Precision
Helmet Recall
Intrusion Precision
Intrusion Recall
False Positive Rate
False Negative Rate
Event Deduplication Accuracy
Processing FPS
```

This should be performed on a separate, representative evaluation set
rather than relying only on model-level metrics.

------------------------------------------------------------------------

# 27. Team/Project Presentation Summary

### One-line explanation

> **HazardLens is an AI-powered workplace safety monitoring system that
> uses computer vision to detect helmet/PPE non-compliance and identify
> workers without required PPE inside restricted work zones.**

### Short technical explanation

> HazardLens uses a dual-model YOLOv8 architecture. A custom-trained
> model detects heads and helmets, while a pretrained YOLOv8 person
> model provides an additional person-detection signal. Detected people
> are checked against a normalized restricted-zone polygon. Helmet
> association determines PPE compliance, and the combined location/PPE
> state is converted into safety events. ByteTrack and event-state logic
> reduce repeated alerts across video frames. The system exposes the
> detection pipeline through both a Streamlit monitoring application and
> a FastAPI/Next.js full-stack dashboard.

### Core innovation

The key architectural idea is not simply:

``` text
Detect person
```

but:

``` text
Detect worker
      +
Determine PPE state
      +
Determine worker location
      +
Combine both states
      ↓
Produce meaningful safety event
```

This lets HazardLens distinguish between:

``` text
PPE violation
```

and:

``` text
Restricted-zone intrusion without required PPE
```

while also attempting to recover workers that are difficult to detect
because of occlusion.

------------------------------------------------------------------------

# 28. License

This repository is currently a project/research prototype.

Before publishing the repository publicly, verify the licenses and
redistribution requirements for:

-   datasets
-   pretrained model weights
-   third-party libraries
-   sample videos
-   generated assets

Do not redistribute third-party assets unless their respective licenses
permit it.

------------------------------------------------------------------------

## ⭐ Project Status

HazardLens currently contains:

-   ✅ YOLOv8-based detection
-   ✅ Custom PPE model
-   ✅ Separate person detection model
-   ✅ Head/helmet proxy person recovery
-   ✅ ByteTrack-based tracking
-   ✅ Restricted-zone geometry
-   ✅ Normalized zone coordinates
-   ✅ Multi-point zone intersection
-   ✅ PPE/zone decision logic
-   ✅ Violation event deduplication
-   ✅ Streamlit monitoring interface
-   ✅ FastAPI backend
-   ✅ SQLite persistence
-   ✅ Next.js dashboard
-   ✅ Incident and zone APIs
-   ⚠️ End-to-end person-recall measurement still required
-   ⚠️ Production authentication not implemented
-   ⚠️ Production-grade live camera/distributed processing not
    implemented

------------------------------------------------------------------------

## 🚀 Quick Start

For the fastest way to try the standalone monitoring application:

``` bash
cd Hazardlens

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

streamlit run app.py
```

Then open:

``` text
http://localhost:8501
```

Upload a suitable workplace/construction video and start monitoring.

------------------------------------------------------------------------

**HazardLens --- Turning visual workplace data into actionable safety
events. 🦺**
