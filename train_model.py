"""
train_model.py – Dataset extraction and face encoding model trainer.

Usage (CLI):
    python train_model.py --zip employees.zip
    python train_model.py --zip employees.zip --dataset dataset/ --model model/face_encodings.pkl

The script:
  1. Extracts the ZIP file into the dataset directory.
  2. Iterates over sub-folders (each folder = one employee name).
  3. Encodes every face found in each image.
  4. Saves a pickled dict {encodings: [...], names: [...]} to the model path.
"""

import os
import sys
import pickle
import zipfile
import logging
import argparse
from pathlib import Path

import cv2
import face_recognition
import numpy as np

# ── Allow running from the project root without installing the package ─────────
sys.path.insert(0, str(Path(__file__).parent))
from config import DATASET_DIR, MODEL_DIR, MODEL_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Step 1 – Extract Dataset ZIP ─────────────────────────────────────────────

def extract_dataset(zip_path: str, output_dir: str = None) -> str:
    """
    Extract a ZIP file containing employee image folders.

    ZIP structure expected:
        employees.zip
        ├── Alice_Smith/
        │   ├── img1.jpg
        │   └── img2.jpg
        └── Bob_Jones/
            └── img1.jpg

    Args:
        zip_path:   Path to the ZIP file.
        output_dir: Where to extract (defaults to config DATASET_DIR).

    Returns:
        Path to the extracted dataset directory.
    """
    output_dir = Path(output_dir or DATASET_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extracting '{zip_path}' → '{output_dir}' …")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(output_dir)

    logger.info("Extraction complete.")
    return str(output_dir)


# ─── Step 2 – Build Face Encodings ────────────────────────────────────────────

def build_encodings(dataset_dir: str = None) -> tuple[list, list]:
    """
    Walk the dataset directory, detect faces in each image, and compute
    128-dimensional encodings.

    Each sub-folder name is treated as the employee's name.
    Multiple photos per employee improve recognition robustness.

    Args:
        dataset_dir: Root of the employee image folders.

    Returns:
        (encodings, names): Parallel lists of face encodings and employee names.
    """
    dataset_dir  = Path(dataset_dir or DATASET_DIR)
    all_encodings: list = []
    all_names:     list = []

    # Discover employee folders
    employee_dirs = [d for d in dataset_dir.iterdir() if d.is_dir()]
    if not employee_dirs:
        # Handle case where ZIP extracted into a single sub-folder
        subdirs = [d for d in dataset_dir.iterdir() if d.is_dir()]
        if subdirs:
            employee_dirs = [d for sub in subdirs for d in sub.iterdir() if d.is_dir()]

    if not employee_dirs:
        logger.error("No employee folders found in the dataset directory.")
        return [], []

    logger.info(f"Found {len(employee_dirs)} employee folder(s): "
                f"{[d.name for d in employee_dirs]}")

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    for emp_dir in sorted(employee_dirs):
        employee_name = emp_dir.name
        image_files   = [
            f for f in emp_dir.iterdir()
            if f.is_file() and f.suffix.lower() in valid_extensions
        ]

        if not image_files:
            logger.warning(f"  [{employee_name}] No images found – skipping.")
            continue

        logger.info(f"  [{employee_name}] Processing {len(image_files)} image(s) …")
        encoded_count = 0

        for img_path in image_files:
            try:
                bgr_img = cv2.imread(str(img_path))
                if bgr_img is None:
                    logger.warning(f"    Could not read: {img_path.name}")
                    continue

                # --- NEW CODE: Resize image to speed up processing ---
                max_width = 600
                if bgr_img.shape[1] > max_width:
                    ratio = max_width / bgr_img.shape[1]
                    dim = (max_width, int(bgr_img.shape[0] * ratio))
                    bgr_img = cv2.resize(bgr_img, dim, interpolation=cv2.INTER_AREA)
                # -----------------------------------------------------

                rgb_img  = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
                locations = face_recognition.face_locations(rgb_img, model="hog")

                if not locations:
                    logger.warning(f"    No face detected: {img_path.name}")
                    continue

                encodings = face_recognition.face_encodings(rgb_img, locations)
                for enc in encodings:
                    all_encodings.append(enc)
                    all_names.append(employee_name)
                    encoded_count += 1

            except Exception as e:
                logger.error(f"    Error processing {img_path.name}: {e}")

        logger.info(f"  [{employee_name}] Encoded {encoded_count} face(s).")

    logger.info(
        f"Total: {len(all_encodings)} encodings across "
        f"{len(set(all_names))} employee(s)."
    )
    return all_encodings, all_names


# ─── Step 3 – Save Model ──────────────────────────────────────────────────────

def save_model(encodings: list, names: list, model_path: str = None) -> str:
    """
    Pickle the encodings and names to disk.

    Args:
        encodings:   List of 128-d numpy arrays.
        names:       Parallel list of employee name strings.
        model_path:  Destination path (defaults to config MODEL_PATH).

    Returns:
        The path where the model was saved.
    """
    model_path = Path(model_path or MODEL_PATH)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"encodings": encodings, "names": names}
    with open(model_path, "wb") as f:
        pickle.dump(data, f)

    logger.info(f"Model saved to '{model_path}'.")
    return str(model_path)


# ─── Full Pipeline ────────────────────────────────────────────────────────────

def train_from_zip(zip_path: str, dataset_dir: str = None, model_path: str = None) -> str:
    """
    Run the complete training pipeline from a ZIP file.

    Returns:
        Path to the saved model, or raises an exception on failure.
    """
    if not Path(zip_path).exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")

    dataset_dir = str(extract_dataset(zip_path, dataset_dir))
    encodings, names = build_encodings(dataset_dir)

    if not encodings:
        raise RuntimeError("No faces were encoded. Check that the ZIP has valid images.")

    return save_model(encodings, names, model_path)


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train the face recognition model from a ZIP of employee images."
    )
    parser.add_argument(
        "--zip",
        required=True,
        help="Path to the ZIP file containing employee image folders.",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Override extraction directory (default: dataset/).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override model output path (default: model/face_encodings.pkl).",
    )
    args = parser.parse_args()

    try:
        saved_path = train_from_zip(args.zip, args.dataset, args.model)
        print(f"\n✅ Training complete! Model saved to: {saved_path}")
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        sys.exit(1)
