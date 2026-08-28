import json
from pathlib import Path

from .database import connect
from .file_store import create_receiving_content

PUBLIC_FIELDS = {"recipient", "tracking", "carrier", "notes"}


def store_parcel(fields: dict, source: str, parser_state: str,carrier:str="") -> int:
    recipient = str(fields.get("recipient", "")).strip()[:120]
    tracking = str(fields.get("tracking", "")).strip()[:120]
    if not carrier:
        carrier = str(fields.get("carrier", "")).strip()[:80]
    if not recipient or not tracking or not carrier:
        raise ValueError("Recipient, tracking number, and carrier are required")

    parameters = {key: value for key, value in fields.items() if key in PUBLIC_FIELDS}
    if parser_state == "alternate":
        parameters = dict(fields)

    file_name, file_path = create_receiving_content(recipient, tracking, carrier)

    try:
        with connect() as db:
            file_cursor = db.execute(
                "INSERT INTO files(name,path) VALUES(?,?)",
                (file_name, file_path),
            )
            file_id = int(file_cursor.lastrowid)
            parcel_cursor = db.execute(
                """
                INSERT INTO parcels(
                    recipient,tracking,carrier,source,parameters,parser_state,file_id
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    recipient,
                    tracking,
                    carrier,
                    source,
                    json.dumps(parameters),
                    parser_state,
                    file_id,
                ),
            )
            return int(parcel_cursor.lastrowid)
    except Exception:
        Path(file_path).unlink(missing_ok=True)
        raise


def recent(limit: int = 20):
    safe_limit = max(1, min(limit, 50))
    with connect() as db:
        rows = db.execute(
            """
            SELECT p.id,p.recipient,p.tracking,p.carrier,p.source,p.created_at,
                   p.processed_at,f.name AS file_name
            FROM parcels p
            JOIN files f ON f.id=p.file_id
            ORDER BY p.id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]
