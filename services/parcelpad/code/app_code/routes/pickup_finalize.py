from flask import Blueprint

from ..auth import login_required
from ..csrf import require_csrf
from ..stages import pickup
from . import finish_safe


bp = Blueprint("pickup_finalize", __name__)


@bp.post("/pickups/<record_id>/finalize")
@login_required
@require_csrf
def finalize(record_id):
    return finish_safe("pickup", pickup, record_id)
