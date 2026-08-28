import sqlite3
from pathlib import Path


DB_PATH = Path("/tmp/pulseboard.db")


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialise_database() -> None:
    with connect() as db:
        db.execute("DROP TABLE IF EXISTS integrations")
        db.execute(
            '''
            CREATE TABLE integrations (
                record_id INTEGER PRIMARY KEY,
                display_name TEXT NOT NULL,
                region_code TEXT NOT NULL,
                priority INTEGER NOT NULL,
                enabled INTEGER NOT NULL,
                health_url TEXT NOT NULL
            )
            '''
        )

        regions = ("eu1","eu2", "us1","us2", "apac", "ops")
        rows = []
        for record_id in range(1, 101):
            region = regions[(record_id - 1) % len(regions)]
            priority = (record_id % 7) + 1
            health_path = "steady"
            rows.append(
                (
                    record_id,
                    f"Connector {record_id:03d}",
                    region,
                    priority,
                    1,
                    f"http://127.0.0.1:9101/probe/{health_path}",
                )
            )

        db.executemany(
            '''
            INSERT INTO integrations(
                record_id,
                display_name,
                region_code,
                priority,
                enabled,
                health_url
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            rows,
        )
