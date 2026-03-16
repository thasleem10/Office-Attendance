"""
config.py – Centralised configuration for the Face Recognition Attendance System.
All tuneable parameters live here; edit this file or set environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
DATASET_DIR    = BASE_DIR / "dataset"
MODEL_DIR      = BASE_DIR / "model"
DATA_DIR       = BASE_DIR / "data"
UPLOAD_DIR     = BASE_DIR / "static" / "uploads"

MODEL_PATH     = MODEL_DIR / "face_encodings.pkl"
CSV_PATH       = DATA_DIR / "attendance.csv"

# ─── Face Recognition ─────────────────────────────────────────────────────────
# Lower tolerance = stricter matching (0.4–0.6 is typical)
RECOGNITION_TOLERANCE = float(os.getenv("RECOGNITION_TOLERANCE", "0.5"))

# ─── Flask ────────────────────────────────────────────────────────────────────
SECRET_KEY  = os.getenv("SECRET_KEY", "change-me-in-production")
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB upload limit
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

# ─── Google Sheets ────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_SHEET_ID         = os.getenv("GOOGLE_SHEET_ID", "")        # Set in .env
GOOGLE_SHEET_NAME       = os.getenv("GOOGLE_SHEET_NAME", "Attendance")

# ─── Attendance ───────────────────────────────────────────────────────────────
CSV_HEADERS = ["Employee Name", "Date", "Check-In Time", "Check-Out Time"]
