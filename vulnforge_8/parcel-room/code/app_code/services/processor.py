import json

from .database import connect
from .file_store import (
    read_managed_content,
    receipt_path_from_managed_content,
    write_receipt,
)


def _content_row(db, content_id: int):
    return db.execute(
        "SELECT id,name,path FROM files WHERE id=?",
        (content_id,),
    ).fetchone()


def process_parcel(parcel_id: int):
    with connect() as db:
        parcel = db.execute(
            "SELECT * FROM parcels WHERE id=?",
            (parcel_id,),
        ).fetchone()
        if parcel is None:
            return None

        content_data = {"content_id": int(parcel["file_id"])}
        parameters = json.loads(parcel["parameters"] or "{}")
        content_data.update(parameters)

        try:
            resolved_content_id = int(content_data["content_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Stored reference is invalid") from exc

        content_row = _content_row(db, resolved_content_id)
        if content_row is None:
            raise ValueError("Stored reference does not exist")

        content = read_managed_content(content_row["path"])
        receipt_path = receipt_path_from_managed_content(content_row["path"])

        db.execute(
            """
            UPDATE parcels
            SET processed_at=CURRENT_TIMESTAMP, processed_file_id=?
            WHERE id=?
            """,
            (content_row["id"], parcel_id),
        )
        return {
            "parcel_id": parcel_id,
            "recipient": parcel["recipient"],
            "tracking": parcel["tracking"],
            "file": {"id": content_row["id"], "name": content_row["name"]},
            "content": content,
            "receipt": {
                "name": receipt_path.name,
                "url": f"/receipts/{content_row['name']}/download",
            },
        }


def processed_result(parcel_id: int):
    with connect() as db:
        parcel = db.execute(
            "SELECT * FROM parcels WHERE id=? AND processed_file_id IS NOT NULL",
            (parcel_id,),
        ).fetchone()
        if parcel is None:
            return None
        content_row = _content_row(db, int(parcel["processed_file_id"]))
        if content_row is None:
            return None

        content = read_managed_content(content_row["path"])
        receipt_path = receipt_path_from_managed_content(content_row["path"])
        return {
            "parcel_id": parcel_id,
            "recipient": parcel["recipient"],
            "tracking": parcel["tracking"],
            "file": {"id": content_row["id"], "name": content_row["name"]},
            "content": content,
            "receipt": {
                "name": receipt_path.name,
                "url": f"/receipts/{content_row['name']}/download",
            },
        }


def receipt_for_download(temp_content_name: str):
    try:
        return write_receipt(temp_content_name, from_managed_name=True)
    except ValueError:
        return None
