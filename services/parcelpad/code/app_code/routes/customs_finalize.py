from flask import Blueprint

from ..auth import login_required
from ..csrf import require_csrf
from ..stages import customs
from . import finish_safe


bp = Blueprint("customs_finalize", __name__)


@bp.post("/customs/<record_id>/finalize")
@login_required
@require_csrf
def finalize(record_id):
    return finish_safe("customs", customs, record_id)
