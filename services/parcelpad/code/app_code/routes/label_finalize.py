from flask import Blueprint

from ..auth import login_required
from ..csrf import require_csrf
from ..stages import label
from . import finish_safe


bp = Blueprint("label_finalize", __name__)


@bp.post("/labels/<record_id>/finalize")
@login_required
@require_csrf
def finalize(record_id):
    return finish_safe("label", label, record_id)
