"""
train_model.py – Dataset extraction utility.
Simplified to remove heavy AI dependencies (dlib, opencv).
The actual face training now happens client-side in the browser.
"""

import os
import zipfile
import logging
from pathlib import Path

# Config import handled by absolute path if needed, but we keep it simple
DATASET_DIR = "dataset"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def extract_dataset(zip_path: str, output_dir: str = None) -> str:
    """
    Extract a ZIP file containing employee image folders.
    """
    output_dir = Path(output_dir or DATASET_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extracting '{zip_path}' → '{output_dir}' …")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(output_dir)

    logger.info("Extraction complete.")
    return str(output_dir)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract dataset.")
    parser.add_argument("--zip", required=True)
    args = parser.parse_args()
    extract_dataset(args.zip)
