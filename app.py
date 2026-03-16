"""
app.py – Flask web application for Employee Face Recognition Attendance System.

Routes:
    GET  /                 – Homepage with upload form
    POST /upload           – Handle face photo upload → recognise → log attendance
    POST /train            – Accept dataset ZIP → retrain model
    GET  /attendance       – Attendance log viewer page
    GET  /attendance/data  – JSON API for attendance table
    GET  /health           – Health check
"""

import os
import sys
import logging
import uuid
from pathlib import Path
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
)

# ── Project root on path ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    SECRET_KEY,
    MAX_CONTENT_LENGTH,
    DEBUG,
    UPLOAD_DIR,
    MODEL_PATH,
)
from src.image_utils import validate_image, read_image_from_upload, resize_for_display
from src.face_recognition_module import run_face_recognition_pipeline
from src.attendance_logger import log_attendance, get_all_attendance
from train_model import train_from_zip

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Flask App Initialisation ──────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key            = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


# ═════════════════════════════════════════════════════════════════════════════
# Routes
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Homepage – employee photo upload form."""
    model_exists = Path(MODEL_PATH).exists()
    return render_template("index.html", model_exists=model_exists)


# ── image_upload_handler() ───────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload():
    """
    Handle employee photo upload.
    1. Validate the image.
    2. Run face detection + recognition.
    3. Log attendance (check-in / check-out).
    4. Return JSON result for AJAX display.
    """
    if "photo" not in request.files:
        return jsonify({"success": False, "error": "No file part in the request."}), 400

    file = request.files["photo"]
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    # ── Validate ──────────────────────────────────────────────────────────────
    is_valid, validation_error = validate_image(file)
    if not is_valid:
        return jsonify({"success": False, "error": validation_error}), 422

    # ── Save uploaded file (for preview display) ──────────────────────────────
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    save_path   = Path(UPLOAD_DIR) / unique_name
    file.save(str(save_path))
    resize_for_display(str(save_path))
    preview_url = f"/static/uploads/{unique_name}"

    # ── Face Recognition ──────────────────────────────────────────────────────
    file.seek(0)
    try:
        rgb_image = read_image_from_upload(file)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to read image: {e}"}), 422

    recognition_result = run_face_recognition_pipeline(rgb_image)

    if not recognition_result["success"]:
        return jsonify({
            "success":     False,
            "error":       recognition_result["error"],
            "preview_url": preview_url,
        }), 200

    employee_name = recognition_result["employee_name"]
    confidence    = recognition_result["confidence"]

    # ── Unknown Employee ──────────────────────────────────────────────────────
    if employee_name == "Unknown":
        return jsonify({
            "success":        False,
            "error":          "Employee not recognised. Please ensure you are in the system.",
            "employee_name":  "Unknown",
            "confidence":     confidence,
            "preview_url":    preview_url,
        }), 200

    # ── Log Attendance ────────────────────────────────────────────────────────
    attendance = log_attendance(employee_name)

    return jsonify({
        "success":         True,
        "employee_name":   employee_name,
        "confidence":      confidence,
        "action":          attendance["action"],
        "date":            attendance["date"],
        "check_in":        attendance.get("check_in"),
        "check_out":       attendance.get("check_out"),
        "message":         attendance["message"],
        "sheets_synced":   attendance["sheets_synced"],
        "preview_url":     preview_url,
    })


# ── Training Route ────────────────────────────────────────────────────────────
@app.route("/train", methods=["GET", "POST"])
def train():
    """Accept a ZIP file and retrain the model."""
    if request.method == "GET":
        return render_template("train.html")

    if "dataset" not in request.files:
        flash("No ZIP file provided.", "error")
        return redirect(url_for("train"))

    zip_file = request.files["dataset"]
    if not zip_file.filename.lower().endswith(".zip"):
        flash("Please upload a .zip file.", "error")
        return redirect(url_for("train"))

    # Save ZIP temporarily
    zip_save_path = Path(UPLOAD_DIR) / f"dataset_{uuid.uuid4().hex}.zip"
    zip_file.save(str(zip_save_path))

    try:
        model_path = train_from_zip(str(zip_save_path))
        flash(f"✅ Model trained successfully and saved to {model_path}", "success")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        flash(f"❌ Training failed: {e}", "error")
    finally:
        # Clean up the temp ZIP
        zip_save_path.unlink(missing_ok=True)

    return redirect(url_for("train"))


# ── Attendance Viewer ─────────────────────────────────────────────────────────
@app.route("/attendance")
def attendance():
    """Attendance log viewer page."""
    records = get_all_attendance()
    today   = datetime.now().strftime("%Y-%m-%d")
    return render_template("attendance.html", records=records, today=today)


@app.route("/attendance/data")
def attendance_data():
    """JSON endpoint for the attendance DataTable."""
    records = get_all_attendance()
    return jsonify({"data": records})


# ── Health Check ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({
        "status":       "ok",
        "model_loaded": Path(MODEL_PATH).exists(),
        "timestamp":    datetime.now().isoformat(),
    })


# ═════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=DEBUG, ssl_context='adhoc')
