"""Patch headless cv2 before ultralytics import (needs attrs at load time)."""
import cv2

# Fail fast if OpenCV binary is broken/missing (namespace-only install).
if not hasattr(cv2, "VideoCapture"):
    raise ImportError(
        "Broken OpenCV install: cv2.VideoCapture missing. "
        "Recreate backend container or reinstall opencv-python-headless."
    )

# OpenCV read/write flags (ultralytics.utils.patches defaults)
for name, val in (
    ("IMREAD_UNCHANGED", -1),
    ("IMREAD_GRAYSCALE", 0),
    ("IMREAD_COLOR", 1),
    ("IMREAD_ANYDEPTH", 2),
    ("IMREAD_ANYCOLOR", 4),
    ("IMWRITE_JPEG_QUALITY", 1),
):
    if not hasattr(cv2, name):
        setattr(cv2, name, val)

if not hasattr(cv2, "imshow"):
    cv2.imshow = lambda *_a, **_k: None  # ponytail: GUI stub for ultralytics import
if not hasattr(cv2, "setNumThreads"):
    cv2.setNumThreads = lambda *_a, **_k: None
