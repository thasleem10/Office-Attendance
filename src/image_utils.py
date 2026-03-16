"""
image_utils.py – Image validation and conversion helpers.
"""

import io
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from config import ALLOWED_EXTENSIONS


def allowed_file(filename: str) -> bool:
    """Return True if the filename has an allowed image extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def validate_image(file_storage) -> tuple[bool, str]:
    """
    Validate that a FileStorage object:
      - Has an allowed extension
      - Is a readable image
      - Contains at least one detectable face

    Returns (is_valid: bool, error_message: str).
    """
    filename = file_storage.filename or ""
    if not allowed_file(filename):
        return False, f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}"

    try:
        file_bytes = file_storage.read()
        file_storage.seek(0)           # Reset stream for later use
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()                   # Raises if not a valid image
    except (UnidentifiedImageError, Exception) as e:
        return False, f"Invalid or corrupted image file: {e}"

    return True, ""


def read_image_from_upload(file_storage) -> np.ndarray:
    """
    Convert a Flask FileStorage into an RGB numpy array suitable
    for face_recognition / OpenCV processing.
    """
    file_bytes = np.frombuffer(file_storage.read(), np.uint8)
    file_storage.seek(0)
    bgr_image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if bgr_image is None:
        raise ValueError("Could not decode image.")
    rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
    return rgb_image


def resize_for_display(image_path: str, max_size: int = 800) -> None:
    """
    Resize a saved image (in-place) so its longest side ≤ max_size pixels.
    Used to keep uploaded previews lightweight.
    """
    img = cv2.imread(image_path)
    if img is None:
        return
    h, w = img.shape[:2]
    scale = min(max_size / max(h, w), 1.0)
    if scale < 1.0:
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(image_path, img)
