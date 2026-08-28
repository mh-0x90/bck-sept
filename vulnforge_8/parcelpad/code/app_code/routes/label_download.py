from flask import Blueprint

from ..auth import login_required
from . import selected_download


bp = Blueprint("label_download", __name__)


@bp.get("/labels/<record_id>/download")
@login_required
def download(record_id):
    return selected_download(
        "label",
        record_id,
        ("shipment_ref", "format", "carrier", "service", "tracking", "route_code"),
        f"{record_id}-label.json",
    )
