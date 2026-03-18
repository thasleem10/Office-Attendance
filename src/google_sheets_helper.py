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
    Authenticate with Google Sheets API. Returns (client, error_message).
    """
    if not GSPREAD_AVAILABLE:
        return None, "gspread or google-auth not installed"

    creds_path = Path(credentials_file).absolute()
    logger.info(f"Attempting to load credentials from: {creds_path}")
    
    if not creds_path.exists():
        return None, f"Credentials file not found at: {creds_path}"
    
    if not creds_path.is_file():
        return None, f"Path exists but is not a file: {creds_path}"

    try:
        creds  = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
        client = gspread.authorize(creds)
        return client, None
    except Exception as e:
        return None, f"Auth Error: {type(e).__name__} | {repr(e)}"


def append_row(sheet_id: str, sheet_name: str, values: list, credentials_file: str):
    """
    Append a single row to a Google Sheet. Returns (success, error_message).
    """
    client, error = get_sheets_client(credentials_file)
    if client is None:
        logger.error(f"Sync failed: {error}")
        return False, error

    try:
        logger.info(f"Opening sheet ID: {sheet_id}")
        sheet    = client.open_by_key(sheet_id)
        
        logger.info(f"Accessing worksheet: {sheet_name}")
        worksheet = sheet.worksheet(sheet_name)
        
        logger.info(f"Appending values: {values}")
        worksheet.append_row(values, value_input_option="USER_ENTERED")
        
        logger.info("Sync successful.")
        return True, None
    except Exception as e:
        error_msg = f"API Error Type: {type(e).__name__} | Details: {repr(e)}"
        logger.error(f"Sync failed: {error_msg}")
        return False, error_msg
