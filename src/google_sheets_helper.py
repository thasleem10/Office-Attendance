"""
google_sheets_helper.py – Google Sheets API client authentication and row append.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy imports so the app starts even without google-auth installed
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.warning(
        "gspread / google-auth not installed. "
        "Google Sheets logging disabled; CSV fallback will be used."
    )

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_sheets_client(credentials_file: str):
    """
    Authenticate with Google Sheets API using a Service Account JSON file.

    Args:
        credentials_file: Path to the service account credentials JSON.

    Returns:
        gspread.Client on success, or None if unavailable / auth fails.
    """
    if not GSPREAD_AVAILABLE:
        return None

    creds_path = Path(credentials_file)
    if not creds_path.exists():
        logger.warning(f"Credentials file not found: {creds_path}")
        return None

    try:
        creds  = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
        client = gspread.authorize(creds)
        logger.info("Google Sheets client authenticated successfully.")
        return client
    except Exception as e:
        logger.error(f"Google Sheets authentication failed: {e}")
        return None


def append_row(sheet_id: str, sheet_name: str, values: list, credentials_file: str) -> bool:
    """
    Append a single row to a Google Sheet.

    Args:
        sheet_id:         The Google Spreadsheet ID (from the URL).
        sheet_name:       Name of the worksheet tab.
        values:           List of cell values to append.
        credentials_file: Path to service account JSON.

    Returns:
        True on success, False on any failure.
    """
    client = get_sheets_client(credentials_file)
    if client is None:
        return False

    try:
        sheet    = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(sheet_name)
        worksheet.append_row(values, value_input_option="USER_ENTERED")
        logger.info(f"Appended row to Google Sheet '{sheet_name}': {values}")
        return True
    except Exception as e:
        logger.error(f"Failed to append row to Google Sheet: {e}")
        return False
