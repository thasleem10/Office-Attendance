"""
app.py – Flask web application for Employee Face Recognition Attendance System.
Refactored for Client-Side Recognition using face-api.js.
"""

import os
import sys
import logging
import uuid
import json
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
    send_from_directory
)

# ── Project root on path ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    SECRET_KEY,
    MAX_CONTENT_LENGTH,
    DEBUG,
    UPLOAD_DIR,
    DATASET_DIR
)
from src.attendance_logger import log_attendance, get_all_attendance
from train_model import extract_dataset

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
Path(DATASET_DIR).mkdir(parents=True, exist_ok=True)

# ═════════════════════════════════════════════════════════════════════════════
# Routes
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Homepage – employee recognition interface."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """
    Handle attendance logging from the client.
    The client sends the recognized name directly.
    """
    data = request.get_json()
    if not data or "employee_name" not in data:
        return jsonify({"success": False, "error": "No employee name provided."}), 400

    employee_name = data["employee_name"]
    
    if employee_name == "Unknown":
        return jsonify({"success": False, "error": "Unknown face detected."}), 200

    # ── Log Attendance ────────────────────────────────────────────────────────
    try:
        attendance = log_attendance(employee_name)
        return jsonify({
            "success":         True,
            "employee_name":   employee_name,
            "action":          attendance["action"],
            "date":            attendance["date"],
            "message":         attendance["message"],
            "sheets_synced":   attendance["sheets_synced"]
        })
    except Exception as e:
        logger.error(f"Failed to log attendance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/employees")
def get_employees():
    """
    Return a list of employees and their reference images.
    Used by face-api.js on the frontend to 'train' the recognizer.
    """
    dataset_path = Path(DATASET_DIR)
    employees = []
    
    if not dataset_path.exists():
        return jsonify(employees)

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    
    # Each subfolder is an employee
    for emp_dir in sorted(dataset_path.iterdir()):
        if emp_dir.is_dir():
            # Get the first image as a reference
            images = [
                f.name for f in emp_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in valid_extensions
            ]
            if images:
                employees.append({
                    "name": emp_dir.name,
                    "image": f"/dataset/{emp_dir.name}/{images[0]}"
                })
    
    return jsonify(employees)


@app.route("/dataset/<path:filename>")
def serve_dataset(filename):
    """Serve images from the dataset directory."""
    return send_from_directory(DATASET_DIR, filename)


@app.route("/train", methods=["GET", "POST"])
def train():
    """Accept a ZIP file and extract it (Training is now client-side)."""
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
        # Just extract. Face-api.js will pick up the new folders in /api/employees
        extract_dataset(str(zip_save_path), DATASET_DIR)
        flash("✅ Dataset updated successfully! The app will reload and relearn faces.", "success")
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        flash(f"❌ Upload failed: {e}", "error")
    finally:
        zip_save_path.unlink(missing_ok=True)

    return redirect(url_for("train"))


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


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route("/test-sync")
def test_sync():
    """Manually trigger a sync test to see the error."""
    from src.attendance_logger import _sync_checkin_to_sheets
    success, error = _sync_checkin_to_sheets("Test_User", datetime.now().strftime("%Y-%m-%d"), "00:00:00")
    return jsonify({"success": success, "error": error})

@app.route("/debug-sheets")
def debug_sheets():
    """Diagnostic endpoint for Google Sheets."""
    from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME
    import json
    
    path = Path(GOOGLE_CREDENTIALS_FILE).absolute()
    diag = []
    
    diag.append(f"Looking for: {path}")
    
    if not path.exists():
        diag.append("❌ File NOT found")
        return jsonify({"status": "error", "logs": diag})
        
    diag.append("✅ File exists")
    
    if not path.is_file():
        diag.append("❌ Path is a directory, not a file!")
        return jsonify({"status": "error", "logs": diag})
    
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            diag.append(f"✅ Read OK. Email: {data.get('client_email')}")
            
        from src.google_sheets_helper import append_row
        success, error = append_row(GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME, ["Debug", datetime.now().isoformat()], GOOGLE_CREDENTIALS_FILE)
        
        if success:
            diag.append("✅ API CONNECTIVITY SUCCESS!")
        else:
            diag.append(f"❌ API FAILED: {error}")
            
    except Exception as e:
        import traceback
        diag.append(f"❌ CRITICAL ERROR: {repr(e)}")
        diag.append(f"Traceback: {traceback.format_exc()}")
        
    import os
    diag.append(f"CWD: {os.getcwd()}")
    diag.append(f"User: {os.getlogin() if hasattr(os, 'getlogin') else 'unknown'}")
        
    return jsonify({"status": "complete", "logs": diag})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
