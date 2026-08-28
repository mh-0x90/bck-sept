from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    app_secret: str
    internal_url: str
    internal_note: str
    cookie_secure: bool
    login_username: str
    login_password: str


def _required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _secret(name, file_name):
    value = os.environ.get(name, "").strip()
    if value:
        return value
    path = os.environ.get(file_name, "").strip()
    if not path:
        raise RuntimeError(f"{name} or {file_name} is required")
    value = Path(path).read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"{file_name} is empty")
    return value


def _internal_url():
    value = _required("INTERNAL_URL")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("INTERNAL_URL must be an HTTP(S) URL")
    return value


def load_settings():
    note = _required("INTERNAL_NOTE")
    if len(note) > 500:
        raise RuntimeError("INTERNAL_NOTE is too long")
    return Settings(
        app_secret=_secret("APP_SECRET", "APP_SECRET_FILE"),
        internal_url=_internal_url(),
        internal_note=note,
        cookie_secure=os.environ.get("COOKIE_SECURE", "1") == "1",
        login_username=_required("LOGIN_USERNAME"),
        login_password=_secret("LOGIN_PASSWORD", "LOGIN_PASSWORD_FILE"),
    )


def internal_context():
    note = _required("INTERNAL_NOTE")
    if len(note) > 500:
        raise RuntimeError("INTERNAL_NOTE is too long")
    return _internal_url(), note


def receiver_token():
    return _secret("RECEIVER_TOKEN", "RECEIVER_TOKEN_FILE")
