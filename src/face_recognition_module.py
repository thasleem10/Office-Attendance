"""
face_recognition_module.py – Face detection, encoding, and employee prediction.
"""

import pickle
import logging
import numpy as np
import face_recognition
from pathlib import Path
from config import MODEL_PATH, RECOGNITION_TOLERANCE

logger = logging.getLogger(__name__)


# ─── Model Loading ────────────────────────────────────────────────────────────

def load_known_faces() -> tuple[list, list]:
    """
    Load pre-trained face encodings and employee names from the pickled model.

    Returns:
        known_encodings (list): List of 128-d face encodings.
        known_names    (list): Parallel list of employee names.

    Raises:
        FileNotFoundError: If the model has not been trained yet.
    """
    if not Path(MODEL_PATH).exists():
        raise FileNotFoundError(
            "No trained model found. "
            "Please train the model first by uploading a dataset ZIP file."
        )

    with open(MODEL_PATH, "rb") as f:
        data = pickle.load(f)

    known_encodings = data.get("encodings", [])
    known_names     = data.get("names", [])
    logger.info(f"Loaded {len(known_encodings)} face encodings for {len(set(known_names))} employees.")
    return known_encodings, known_names


# ─── Face Detection & Encoding ───────────────────────────────────────────────

def detect_and_encode_face(rgb_image: np.ndarray) -> tuple[list, list]:
    """
    Detect all faces in an RGB image and compute their 128-d encodings.

    Args:
        rgb_image: An RGB numpy array (H, W, 3).

    Returns:
        face_encodings (list): List of 128-d encodings, one per detected face.
        face_locations (list): Bounding boxes as (top, right, bottom, left).
    """
    # Use CNN model for better accuracy, HOG for speed
    # HOG is faster and works well for single-face uploads
    face_locations = face_recognition.face_locations(rgb_image, model="hog")

    if not face_locations:
        logger.warning("No face detected in the uploaded image.")
        return [], []

    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
    logger.info(f"Detected {len(face_locations)} face(s).")
    return face_encodings, face_locations


# ─── Employee Prediction ──────────────────────────────────────────────────────

def predict_employee(
    face_encoding: np.ndarray,
    known_encodings: list,
    known_names: list,
    tolerance: float = None,
) -> tuple[str, float]:
    """
    Compare an uploaded face encoding against all known employee encodings
    and return the best-matching employee name and confidence score.

    Args:
        face_encoding:   128-d encoding of the uploaded face.
        known_encodings: List of known encodings from the trained model.
        known_names:     Employee name parallel to each encoding.
        tolerance:       Max distance to consider a match (default from config).

    Returns:
        (employee_name, confidence)  where confidence is 0–100 %.
        Returns ("Unknown", 0.0) if no match is found.
    """
    if tolerance is None:
        tolerance = RECOGNITION_TOLERANCE

    # Euclidean distances to all known faces
    distances = face_recognition.face_distance(known_encodings, face_encoding)

    if len(distances) == 0:
        return "Unknown", 0.0

    # Best match
    best_idx      = int(np.argmin(distances))
    best_distance = float(distances[best_idx])

    if best_distance > tolerance:
        logger.info(f"No confident match (best distance={best_distance:.3f}, tolerance={tolerance}).")
        return "Unknown", 0.0

    # Convert distance → confidence percentage (0 distance = 100 %)
    confidence = round((1 - best_distance) * 100, 1)
    employee   = known_names[best_idx]
    logger.info(f"Predicted: {employee} | distance={best_distance:.3f} | confidence={confidence}%")
    return employee, confidence


# ─── High-Level Prediction Pipeline ──────────────────────────────────────────

def run_face_recognition_pipeline(rgb_image: np.ndarray) -> dict:
    """
    Full pipeline: detect face → predict employee.

    Returns a result dict with keys:
        success       (bool)
        employee_name (str)
        confidence    (float)
        error         (str | None)
    """
    result = {"success": False, "employee_name": None, "confidence": 0.0, "error": None}

    # 1. Load model
    try:
        known_encodings, known_names = load_known_faces()
    except FileNotFoundError as e:
        result["error"] = str(e)
        return result

    if not known_encodings:
        result["error"] = "The model has no face encodings. Please retrain with employee images."
        return result

    # 2. Detect face
    face_encodings, face_locations = detect_and_encode_face(rgb_image)
    if not face_encodings:
        result["error"] = (
            "No face detected in the uploaded image. "
            "Please upload a clear, front-facing photo."
        )
        return result

    # 3. Predict (use first detected face)
    employee, confidence = predict_employee(face_encodings[0], known_encodings, known_names)

    result["success"]       = True
    result["employee_name"] = employee
    result["confidence"]    = confidence

    if employee == "Unknown":
        result["error"] = "Face not recognised. Make sure the employee is in the dataset."

    return result
