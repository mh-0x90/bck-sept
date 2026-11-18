import sqlite3

from . import records_schema
from ..config import database_path


def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def _remove_legacy_receipt_path(db):
    columns = {row["name"] for row in db.execute("PRAGMA table_info(parcels)").fetchall()}
    if "receipt_path" not in columns:
        return

    db.executescript(
        """
        PRAGMA foreign_keys=OFF;
        BEGIN;
        CREATE TABLE parcels_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            tracking TEXT NOT NULL,
            carrier TEXT NOT NULL,
            source TEXT NOT NULL,
            parameters TEXT NOT NULL DEFAULT '{}',
            parser_state TEXT NOT NULL DEFAULT 'standard',
            file_id INTEGER NOT NULL,
            processed_file_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            processed_at TEXT,
            FOREIGN KEY(file_id) REFERENCES files(id),
            FOREIGN KEY(processed_file_id) REFERENCES files(id)
        );
        INSERT INTO parcels_new(
            id,recipient,tracking,carrier,source,parameters,parser_state,
            file_id,processed_file_id,created_at,processed_at
        )
        SELECT
            id,recipient,tracking,carrier,source,parameters,parser_state,
            file_id,processed_file_id,created_at,processed_at
        FROM parcels;
        DROP TABLE parcels;
        ALTER TABLE parcels_new RENAME TO parcels;
        COMMIT;
        PRAGMA foreign_keys=ON;
        """
    )


def init_db():
    with connect() as db:
        db.executescript(records_schema.SCHEMA)
        _remove_legacy_receipt_path(db)
