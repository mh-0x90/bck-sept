from flask import Blueprint, url_for

from ..auth import login_required
from ..csrf import require_csrf
from ..stages import label
from . import render_flow_page


bp = Blueprint("label_page", __name__)


@bp.route("/labels/<record_id>", methods=["GET", "POST"])
@login_required
@require_csrf
def page(record_id):
    return render_flow_page(
        "label",
        label,
        record_id,
        url_for("label_finalize.finalize", record_id=record_id),
        url_for("label_download.download", record_id=record_id),
    )
