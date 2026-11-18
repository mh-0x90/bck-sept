from flask import Blueprint

from ..auth import login_required
from . import selected_download


bp = Blueprint("delivery_download", __name__)


@bp.get("/deliveries/<record_id>/download")
@login_required
def download(record_id):
    return selected_download(
        "delivery",
        record_id,
        ("tracking", "recipient", "location", "location_type", "method", "delivered_on", "carrier", "proof_ref"),
        f"{record_id}-delivery.json",
    )
