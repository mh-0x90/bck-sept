from flask import Blueprint

from ..auth import login_required
from . import selected_download


bp = Blueprint("customs_download", __name__)


@bp.get("/customs/<record_id>/download")
@login_required
def download(record_id):
    return selected_download(
        "customs",
        record_id,
        ("declaration_ref", "exporter", "importer", "destination_country", "currency", "items", "total_value"),
        f"{record_id}-declaration.json",
    )
