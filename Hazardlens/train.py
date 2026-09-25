"""
Hazardlens - Training Script
------------------------------
Fine-tunes a pretrained YOLOv8 model on the Hard Hat Workers dataset
(classes: head, helmet, person).

HOW TO USE:
1. Place the downloaded dataset folder (from Roboflow) anywhere, e.g. ./dataset
   It should contain: data.yaml, train/, valid/, test/
2. Open data.yaml and update the 'path' field to point to your dataset folder
   (or just pass the correct path below).
3. Run: python train.py

Recommended: run this in Google Colab with a free GPU (Runtime > Change
runtime type > GPU) for much faster training than a laptop CPU.
"""

import torch
from ultralytics import YOLO


def get_device():
    """Use Apple Silicon GPU (MPS) if available, else fall back to CPU."""
    if torch.backends.mps.is_available():
        print("Using Apple Silicon GPU (MPS) for training")
        return "mps"
    print("MPS not available, falling back to CPU (this will be slow)")
    return "cpu"


def train():
    # yolov8n.pt = "nano" version - smallest and fastest, good for a
    # hackathon MVP. Swap for yolov8s.pt if you have more time/compute
    # and want higher accuracy.
    model = YOLO("yolov8n.pt")

    results = model.train(
        data="dataset/data.yaml",   # <-- update this path to your dataset
        epochs=30,                  # 30 is a good balance of speed vs accuracy
        imgsz=640,
        batch=16,
        project="runs",
        name="safezone_ai",
        patience=10,                # stop early if no improvement
        device=get_device(),
    )

    print("\nTraining complete!")
    print(f"Best weights saved at: runs/safezone_ai/weights/best.pt")
    print("Copy that file into this project folder before running app.py")


if __name__ == "__main__":
    train()
