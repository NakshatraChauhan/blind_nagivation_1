"""Configuration values for BlindNav AI."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model" / "yolov8n.pt"

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

# Speech settings
VOICE_COOLDOWN_SECONDS = 3.0
MESSAGE_DEDUP_WINDOW_SECONDS = 5.0

# Logging
LOG_LEVEL = "INFO"
