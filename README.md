# SafeZone AI

Real-time workplace safety monitoring: upload a video, and the system
detects **missing helmets (PPE non-compliance)** and **restricted-zone
intrusions**, showing live-annotated video plus a violation log on a
Streamlit dashboard.

No webcam/live camera support — this works purely on uploaded video files.

---

## 📁 File Structure

```
SafeZoneAI/
├── train.py           # Fine-tunes YOLOv8 on the Hard Hat Workers dataset
├── detector.py         # Core detection pipeline: PPE check + zone check
├── zone_utils.py        # Restricted-zone polygon logic + calibration tool
├── app.py             # Streamlit dashboard (upload video, see results)
├── requirements.txt      # All Python dependencies (free/open source)
├── .gitignore          # Excludes dataset, venv, cache files from git
├── README.md           # This file
│
├── dataset/            # (You add this) Downloaded Hard Hat Workers dataset
│   ├── data.yaml
│   ├── train/
│   ├── valid/
│   └── test/
│
└── best.pt             # (Generated after training) Your trained model weights
```

---

## 🚀 Full Setup — From an Empty Folder to Running App

### Step 1: Set up your environment

```bash
# Create a virtual environment (keeps dependencies isolated)
python3 -m venv venv

# Activate it
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# Install all dependencies
pip3 install -r requirements.txt
```

### Step 2: Get the dataset

1. Go to [universe.roboflow.com/joseph-nelson/hard-hat-workers](https://universe.roboflow.com/joseph-nelson/hard-hat-workers)
2. Click the **"Dataset"** tab
3. Select version **v10 "raw_AllClasses"** (has all 3 classes: head, helmet, person)
4. Click **"Download Dataset"** → choose format **YOLOv8** → sign in with a free account
5. Choose **"Download dataset"** → **zip file**
6. Unzip it, rename the folder to exactly `dataset`, and place it in this project's root folder

Verify `dataset/data.yaml` lists all 3 classes (`head`, `helmet`, `person`).

### Step 3: Train the model

```bash
python3 train.py
```

- This automatically uses your GPU if available: Apple Silicon (MPS), NVIDIA (CUDA), or falls back to CPU.
- Takes ~10-20 min on a GPU/MPS-enabled Mac, much longer on CPU-only machines.
- **If training is too slow on your machine**: run the same `train.py` in [Google Colab](https://colab.research.google.com) with a free T4 GPU instead (upload your dataset, install `ultralytics`, run the script, download `best.pt` when done).

### Step 4: Locate and place your trained weights

```bash
find . -name "best.pt"
```

Copy the newest one into the project root:
```bash
cp ./runs/detect/runs/safezone_ai*/weights/best.pt ./best.pt
```

### Step 5: Get a demo video

You need a video that shows:
- Someone **with** a helmet (compliant)
- Someone **without** a helmet (PPE violation)
- Someone entering a specific area (for zone intrusion)

Either film your own short clip, or use existing footage — just make sure it has clear people/heads visible.

### Step 6: Calibrate the restricted zone

```bash
python3 zone_utils.py your_demo_video.mp4
```

- A window opens showing the first frame of your video
- **Click 4+ points** to trace the area you want to mark as "restricted" (e.g. around hazardous equipment, a work zone, etc.)
- Press **`q`** when done — it prints the coordinates in the terminal

Copy those coordinates and paste them into the `RESTRICTED_ZONE` list near the top of `zone_utils.py`, replacing the placeholder values.

### Step 7: Run the app

```bash
streamlit run app.py
```

This opens a browser tab automatically (usually `localhost:8501`). In the dashboard:
1. Use the sidebar to **upload your demo video**
2. Adjust the confidence slider if needed (default 0.4 is a good starting point)
3. Click **"▶ Start monitoring"**
4. Watch the video play with live bounding boxes:
   - 🟢 **Green** = compliant (helmet detected)
   - 🔴 **Red** = PPE violation (no helmet)
   - 🟠 **Orange** = zone intrusion
   - 🔵 **Blue** = person tracked, no issue
5. Watch the **live violation log** and **stat cards** update on the right

---

## 🌐 Deploying (so others can access it via a link)

1. Push this project to a GitHub repo (dataset/ and venv/ are already gitignored)
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub
3. Click **"New app"**, select your repo, set the main file to `app.py`
4. Click **Deploy**

**Note on `best.pt`**: check its size with `ls -lh best.pt`. If under ~90MB,
commit it directly to git so it deploys with the app. If larger, you'll
need Git LFS or a download-at-startup approach (ask for this code if needed).

---

## 🔧 Tuning Tips

- **Too many false "NO HELMET" flags?** Raise the confidence slider, or
  increase the IOU overlap threshold in `detector.py` (`> 0.2` → try `> 0.3`)
- **Low training accuracy?** Try `yolov8s.pt` instead of `yolov8n.pt` in
  `train.py` (slower but more accurate), or train for more epochs
- **Video processing feels slow?** Lower the video resolution before
  uploading, or reduce `imgsz` in `detector.py`'s model call

---

## ✅ What's Included vs. What You Provide

| Included | You need to provide |
|---|---|
| Full training pipeline | The dataset (free download, steps above) |
| Full detection logic (PPE + zone) | A trained `best.pt` (generated by running `train.py`) |
| Full polished Streamlit dashboard | A demo video |
| Zone calibration tool | Your specific zone coordinates (from the calibration tool) |
