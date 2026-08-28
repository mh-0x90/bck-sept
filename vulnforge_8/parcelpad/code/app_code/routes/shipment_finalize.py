from flask import Blueprint, abort, jsonify

from ..auth import login_required
from ..csrf import require_csrf
from ..repository import Repository
from ..stages import shipment


bp = Blueprint("shipment_finalize", __name__)


@bp.post("/shipments/<record_id>/finalize")
@login_required
@require_csrf
def finalize(record_id):
    repo = Repository()
    record = repo.get_record("shipment", record_id)
    if record is None:
        abort(404)
    if record["stage"] != 9:
        return jsonify({"ok": False, "message": "Shipment is not ready for final processing."}), 409
    try:
        shipment.stage_9(record, repo)
        ok = shipment.stage_10(record, repo)
        message = "Processing complete." if ok else "Processing complete with a delivery error."
        return jsonify({"ok": ok, "message": message})
    except ValueError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400
