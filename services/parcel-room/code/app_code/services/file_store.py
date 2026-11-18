import os
import re
import secrets
import tempfile
from pathlib import Path

from ..config import MAX_FILE_BYTES, RECEIPT_DIR, TMP_FILE_DIR
from .tmp_crypto import decrypt_text, encrypt_text

_RECEIPT_LINE = re.compile(r"^Receipt:\s*(receipts/[/A-Za-z0-9._-]+)\s*$", re.MULTILINE)
_MAX_ENCRYPTED_FILE_BYTES = MAX_FILE_BYTES + 64


def create_receiving_content(recipient: str, tracking: str, carrier: str) -> tuple[str, str]:
    TMP_FILE_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)

    receipt_id = f"{secrets.token_hex(6)}-{carrier}"
    content = (
        "Parcel receiving record\n"
        f"Recipient: {recipient}\n"
        f"Tracking: {tracking}\n"
        f"Carrier: {carrier}\n"
        f"Receipt: receipts/{receipt_id}\n"
    )

    encrypted = encrypt_text(content)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix="receiving-",
        suffix=".enc",
        dir=TMP_FILE_DIR,
        delete=False,
    ) as handle:
        handle.write(encrypted)
        handle.flush()
        os.fsync(handle.fileno())
        path = Path(handle.name)
    os.chmod(path, 0o600)
    return path.name, str(path)


def _managed_path(path_value: str) -> Path:
    root = TMP_FILE_DIR.resolve()
    path = Path(path_value).resolve()
    if root not in path.parents:
        raise ValueError("File record is outside the managed directory")
    if not path.is_file():
        raise ValueError("File record is unavailable")
    if path.stat().st_size > _MAX_ENCRYPTED_FILE_BYTES:
        raise ValueError("File record is too large")
    return path


def _managed_path_from_name(content_name: str) -> Path:
    if not content_name or Path(content_name).name != content_name:
        raise ValueError("Invalid managed file name")
    if not content_name.startswith("receiving-") or not content_name.endswith(".enc"):
        raise ValueError("Invalid managed file name")
    return _managed_path(str(TMP_FILE_DIR / content_name))


def read_managed_content(path_value: str) -> str:
    path = _managed_path(path_value)
    return decrypt_text(path.read_bytes())


def read_managed_content_by_name(content_name: str) -> str:
    path = _managed_path_from_name(content_name)
    return decrypt_text(path.read_bytes())


def _receipt_path_from_content(content: str) -> Path:
    match = _RECEIPT_LINE.search(content)
    if match is None:
        raise ValueError("Receipt reference is missing from the file record")

    relative = Path(match.group(1))
    receipt_path = (RECEIPT_DIR / relative.name).resolve()
    receipt_root = RECEIPT_DIR.resolve()
    if receipt_root not in receipt_path.parents:
        raise ValueError("Receipt is outside the receipt directory")
    return receipt_path


def receipt_path_from_managed_content(source_path: str) -> Path:
    return _receipt_path_from_content(read_managed_content(source_path))


def write_receipt(source: str, *, from_managed_name: bool = False) -> Path:
    if from_managed_name:
        content = read_managed_content_by_name(source)
    else:
        content = read_managed_content(source)

    receipt_path = _receipt_path_from_content(content)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)

    fd, staging_name = tempfile.mkstemp(prefix=".receipt-", dir=RECEIPT_DIR)
    staging = Path(staging_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(staging, 0o600)
        os.replace(staging, receipt_path)
    finally:
        staging.unlink(missing_ok=True)
    return receipt_path


def read_receipt_for_managed_content(source_path: str) -> str:
    path = receipt_path_from_managed_content(source_path)
    if not path.is_file():
        raise ValueError("Receipt is unavailable")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Receipt is too large")
    return path.read_text(encoding="utf-8")
