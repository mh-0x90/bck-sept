from flask import Blueprint, url_for

from ..auth import login_required
from ..csrf import require_csrf
from ..stages import shipment
from . import render_flow_page


bp = Blueprint("shipment_page", __name__)


@bp.route("/shipments/<record_id>", methods=["GET", "POST"])
@login_required
@require_csrf
def page(record_id):
    return render_flow_page(
        "shipment",
        shipment,
        record_id,
        url_for("shipment_finalize.finalize", record_id=record_id),
        url_for("shipment_download.download", record_id=record_id),
    )
