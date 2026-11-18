from flask import Blueprint, url_for

from ..auth import login_required
from ..csrf import require_csrf
from ..stages import pickup
from . import render_flow_page


bp = Blueprint("pickup_page", __name__)


@bp.route("/pickups/<record_id>", methods=["GET", "POST"])
@login_required
@require_csrf
def page(record_id):
    return render_flow_page(
        "pickup",
        pickup,
        record_id,
        url_for("pickup_finalize.finalize", record_id=record_id),
        url_for("pickup_download.download", record_id=record_id),
    )
