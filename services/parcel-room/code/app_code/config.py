import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_NAME = "Parcel Room"
MAX_REQUEST_BYTES = 256 * 1024
RATE_LIMIT_COUNT = 60
RATE_LIMIT_WINDOW_SECONDS = 60
TMP_FILE_DIR = Path("/tmp/parcel-room")
RECEIPT_DIR = BASE_DIR / "receipts"
MAX_FILE_BYTES = 64 * 1024


def database_path() -> Path:
    return Path(os.getenv("PARCEL_DB_PATH", BASE_DIR / "data" / "parcel_room.db"))
