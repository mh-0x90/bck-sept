from flask import Blueprint

from ..auth import login_required
from . import selected_download


bp = Blueprint("pickup_download", __name__)


@bp.get("/pickups/<record_id>/download")
@login_required
def download(record_id):
    return selected_download(
        "pickup",
        record_id,
        ("pickup_ref", "contact", "location", "window_start", "window_end", "parcel_count", "service", "carrier"),
        f"{record_id}-pickup.json",
    )
