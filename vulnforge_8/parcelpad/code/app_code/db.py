import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def _required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _database_password():
    value = os.environ.get("DATABASE_PASSWORD", "").strip()
    if value:
        return value
    path = _required("DATABASE_PASSWORD_FILE")
    value = Path(path).read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("DATABASE_PASSWORD_FILE is empty")
    return value


def connect_db():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    common = {
        "autocommit": True,
        "connect_timeout": 5,
        "row_factory": dict_row,
    }
    if database_url:
        return psycopg.connect(database_url, **common)
    return psycopg.connect(
        host=_required("DATABASE_HOST"),
        port=int(os.environ.get("DATABASE_PORT", "5432")),
        dbname=_required("DATABASE_NAME"),
        user=_required("DATABASE_USER"),
        password=_database_password(),
        **common,
    )
