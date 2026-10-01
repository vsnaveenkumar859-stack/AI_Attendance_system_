import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"

FACES_DIR = DATA_DIR / "faces"
MODELS_DIR = DATA_DIR / "models"
EXPORTS_DIR = DATA_DIR / "exports"
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

# Database
DB_PATH = DATA_DIR / "attendance.db"

# Ensure runtime directories exist
for directory in [DATA_DIR, FACES_DIR, MODELS_DIR, EXPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Face Recognition Models
YUNET_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

YUNET_MODEL_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL_PATH = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
EMBEDDINGS_CACHE_PATH = MODELS_DIR / "embeddings_cache.json"

# Face Recognition Parameters
# SFace cosine similarity ranges from -1 to 1 (higher = more similar). Standard threshold ~0.363 - 0.45
DEFAULT_COSINE_THRESHOLD = 0.45
DEFAULT_DETECTION_CONFIDENCE = 0.75
DEFAULT_NMS_THRESHOLD = 0.3

# Attendance Rules
DEFAULT_LATE_CUTOFF = "09:30"
DUPLICATE_COOLDOWN_SECONDS = 8

# App Info
APP_NAME = "AI Attendance System"
APP_VERSION = "1.0.0"
HOST = "127.0.0.1"
PORT = 8000
