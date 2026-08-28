from flask import Blueprint, url_for

from ..auth import login_required
from ..csrf import require_csrf
from ..stages import delivery
from . import render_flow_page


bp = Blueprint("delivery_page", __name__)


@bp.route("/deliveries/<record_id>", methods=["GET", "POST"])
@login_required
@require_csrf
def page(record_id):
    return render_flow_page(
        "delivery",
        delivery,
        record_id,
        url_for("delivery_finalize.finalize", record_id=record_id),
        url_for("delivery_download.download", record_id=record_id),
    )
