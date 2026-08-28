import json

from flask import Blueprint, Response

from ..auth import login_required
from . import get_record


bp = Blueprint("shipment_download", __name__)


@bp.get("/shipments/<record_id>/download")
@login_required
def download(record_id):
    record = get_record("shipment", record_id)
    body = json.dumps(record["payload"], indent=2, sort_keys=True).encode("utf-8")
    return Response(
        body,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{record_id}-shipment.json"'},
    )
