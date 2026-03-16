"""
attendance_logger.py – Attendance recording with check-in / check-out logic.

Rules:
  - First recognition in a day  → records Check-In time.
  - Second recognition in a day → records Check-Out time.
  - Subsequent recognitions on the same day → ignored (no duplicate).

Storage:
  Primary  – Google Sheets (if credentials.json + GOOGLE_SHEET_ID are configured).
  Fallback – Local CSV file at data/attendance.csv.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path

from config import (
    CSV_PATH,
    CSV_HEADERS,
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_SHEET_ID,
    GOOGLE_SHEET_NAME,
)
from src.google_sheets_helper import append_row

logger = logging.getLogger(__name__)


# ─── CSV Helpers ──────────────────────────────────────────────────────────────

def _ensure_csv() -> None:
    """Create the CSV file with headers if it does not exist."""
    Path(CSV_PATH).parent.mkdir(parents=True, exist_ok=True)
    if not Path(CSV_PATH).exists():
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def _read_csv_records() -> list[dict]:
    """Return all rows from the CSV as a list of dicts."""
    _ensure_csv()
    with open(CSV_PATH, "r", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv_records(records: list[dict]) -> None:
    """Overwrite the entire CSV with the given records."""
    _ensure_csv()
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(records)


# ─── Core Logic ───────────────────────────────────────────────────────────────

def get_today_record(employee_name: str) -> dict | None:
    """
    Return today's attendance record for an employee, or None if not found.

    Checks the local CSV which acts as the ground truth for daily state.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    for row in _read_csv_records():
        if row["Employee Name"] == employee_name and row["Date"] == today:
            return row
    return None


def log_attendance(employee_name: str) -> dict:
    """
    Record check-in or check-out for the given employee.

    Returns a status dict:
        action       (str)   – "check_in" | "check_out" | "already_complete"
        employee     (str)
        date         (str)
        check_in     (str)
        check_out    (str | None)
        message      (str)
        sheets_synced (bool)
    """
    now       = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    time_str  = now.strftime("%H:%M:%S")

    existing = get_today_record(employee_name)

    # ── Already checked in AND checked out ────────────────────────────────────
    if existing and existing.get("Check-Out Time"):
        return {
            "action":        "already_complete",
            "employee":      employee_name,
            "date":          today_str,
            "check_in":      existing["Check-In Time"],
            "check_out":     existing["Check-Out Time"],
            "message":       f"{employee_name} has already completed attendance for today.",
            "sheets_synced": False,
        }

    # ── Check-Out (already checked in, no check-out yet) ─────────────────────
    if existing and not existing.get("Check-Out Time"):
        records = _read_csv_records()
        for row in records:
            if row["Employee Name"] == employee_name and row["Date"] == today_str:
                row["Check-Out Time"] = time_str
                break
        _write_csv_records(records)

        synced = _sync_checkout_to_sheets(employee_name, today_str, time_str)

        return {
            "action":        "check_out",
            "employee":      employee_name,
            "date":          today_str,
            "check_in":      existing["Check-In Time"],
            "check_out":     time_str,
            "message":       f"✅ Check-Out recorded for {employee_name} at {time_str}",
            "sheets_synced": synced,
        }

    # ── Check-In (first recognition of the day) ───────────────────────────────
    new_row = {
        "Employee Name":  employee_name,
        "Date":           today_str,
        "Check-In Time":  time_str,
        "Check-Out Time": "",
    }

    records = _read_csv_records()
    records.append(new_row)
    _write_csv_records(records)

    synced = _sync_checkin_to_sheets(employee_name, today_str, time_str)

    return {
        "action":        "check_in",
        "employee":      employee_name,
        "date":          today_str,
        "check_in":      time_str,
        "check_out":     None,
        "message":       f"✅ Check-In recorded for {employee_name} at {time_str}",
        "sheets_synced": synced,
    }


# ─── Google Sheets Sync ───────────────────────────────────────────────────────

def _sync_checkin_to_sheets(employee_name: str, date: str, check_in: str) -> bool:
    """Append a new check-in row to Google Sheets (check-out column left blank)."""
    if not GOOGLE_SHEET_ID:
        return False
    return append_row(
        sheet_id=GOOGLE_SHEET_ID,
        sheet_name=GOOGLE_SHEET_NAME,
        values=[employee_name, date, check_in, ""],
        credentials_file=GOOGLE_CREDENTIALS_FILE,
    )


def _sync_checkout_to_sheets(employee_name: str, date: str, check_out: str) -> bool:
    """
    Update the existing Google Sheets row with check-out time.
    This implementation appends an update marker row since the Sheets API
    requires knowing the exact row index for in-place updates.
    For production, consider using a Sheets cell finding approach.
    """
    if not GOOGLE_SHEET_ID:
        return False
    return append_row(
        sheet_id=GOOGLE_SHEET_ID,
        sheet_name=GOOGLE_SHEET_NAME,
        values=[employee_name, date, "(see check-in row)", check_out],
        credentials_file=GOOGLE_CREDENTIALS_FILE,
    )


# ─── Report Queries ───────────────────────────────────────────────────────────

def get_all_attendance() -> list[dict]:
    """Return all attendance records from the CSV, newest first."""
    records = _read_csv_records()
    return list(reversed(records))


def get_attendance_for_date(date_str: str) -> list[dict]:
    """Return attendance records for a specific date (YYYY-MM-DD)."""
    return [r for r in _read_csv_records() if r.get("Date") == date_str]
