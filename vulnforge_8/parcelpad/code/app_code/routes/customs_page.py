from flask import Blueprint, url_for

from ..auth import login_required
from ..csrf import require_csrf
from ..stages import customs
from . import render_flow_page


bp = Blueprint("customs_page", __name__)


@bp.route("/customs/<record_id>", methods=["GET", "POST"])
@login_required
@require_csrf
def page(record_id):
    return render_flow_page(
        "customs",
        customs,
        record_id,
        url_for("customs_finalize.finalize", record_id=record_id),
        url_for("customs_download.download", record_id=record_id),
    )
