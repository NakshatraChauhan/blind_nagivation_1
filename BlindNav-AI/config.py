"""Configuration values for BlindNav AI."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model" / "yolov8n.pt"
SEAFORMER_ONNX_PATH = BASE_DIR / "model" / "seaformer_b0.onnx"

# Camera and inference settings
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
TARGET_FPS = 15

# YOLO settings
CONF_THRESHOLD = 0.35
IOU_THRESHOLD = 0.45
IMPORTANT_OBJECTS = {"person", "car", "bus", "truck", "bicycle", "dog"}

# Distance thresholds (px)
VERY_CLOSE_WIDTH = 300
NEAR_WIDTH = 150

# SeaFormer segmentation settings
SEG_INPUT_WIDTH = 512
SEG_INPUT_HEIGHT = 512
SEG_BLUR_KERNEL = 7
SEG_TEMPORAL_ALPHA = 0.65
SEG_OCCUPANCY_ALERT_THRESHOLD = 0.30
SEG_OCCUPANCY_HIGH_THRESHOLD = 0.45

# Speech settings
VOICE_COOLDOWN_SECONDS = 3.0
MESSAGE_DEDUP_WINDOW_SECONDS = 5.0

# Logging
LOG_LEVEL = "INFO"
