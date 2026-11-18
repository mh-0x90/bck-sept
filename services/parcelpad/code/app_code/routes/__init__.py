import json

from flask import abort, jsonify, render_template, request, Response

from ..repository import Repository


FLOW_LABELS = {
    "shipment": "Shipment",
    "label": "Shipping label",
    "pickup": "Pickup",
    "customs": "Customs declaration",
    "delivery": "Delivery confirmation",
}


def get_record(flow_type, record_id):
    record = Repository().get_record(flow_type, record_id)
    if record is None:
        abort(404)
    return record


def render_flow_page(flow_type, flow, record_id, finalize_endpoint, download_endpoint):
    repo = Repository()
    record = repo.get_record(flow_type, record_id)
    if record is None:
        abort(404)
    error = None
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "back" and 1 < record["stage"] < 10:
                repo.set_stage(record_id, record["stage"] - 1, "ready")
            elif action == "next" and 1 <= record["stage"] <= 8:
                flow.run_stage(record["stage"], record, repo)
                repo.set_stage(record_id, record["stage"] + 1, "ready")
            else:
                abort(400)
            record = repo.get_record(flow_type, record_id)
        except ValueError as exc:
            error = str(exc)
    return render_template(
        "flow.html",
        record=record,
        flow_label=FLOW_LABELS[flow_type],
        stage_title=flow.STAGE_TITLES[record["stage"] - 1],
        fields=flow.view_fields(record),
        finalize_endpoint=finalize_endpoint,
        download_endpoint=download_endpoint,
        error=error,
    ), 400 if error else 200


def finish_safe(flow_type, flow, record_id):
    repo = Repository()
    record = repo.get_record(flow_type, record_id)
    if record is None:
        abort(404)
    if record["stage"] != 9:
        return jsonify({"ok": False, "message": "Record is not ready for final processing."}), 409
    try:
        flow.stage_9(record, repo)
        ok = flow.stage_10(record, repo)
        return jsonify({"ok": bool(ok), "message": "Processing complete."})
    except ValueError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


def selected_download(flow_type, record_id, fields, filename):
    record = get_record(flow_type, record_id)
    payload = {key: record["payload"].get(key) for key in fields}
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    return Response(
        body,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def register_routes(app):
    from .customs_download import bp as customs_download_bp
    from .customs_finalize import bp as customs_finalize_bp
    from .customs_page import bp as customs_page_bp
    from .delivery_download import bp as delivery_download_bp
    from .delivery_finalize import bp as delivery_finalize_bp
    from .delivery_page import bp as delivery_page_bp
    from .home import bp as home_bp
    from .label_download import bp as label_download_bp
    from .login import bp as login_bp
    from .logout import bp as logout_bp
    from .label_finalize import bp as label_finalize_bp
    from .label_page import bp as label_page_bp
    from .pickup_download import bp as pickup_download_bp
    from .pickup_finalize import bp as pickup_finalize_bp
    from .pickup_page import bp as pickup_page_bp
    from .shipment_download import bp as shipment_download_bp
    from .shipment_finalize import bp as shipment_finalize_bp
    from .shipment_page import bp as shipment_page_bp

    for blueprint in (
        login_bp,
        logout_bp,
        home_bp,
        shipment_page_bp,
        shipment_finalize_bp,
        shipment_download_bp,
        label_page_bp,
        label_finalize_bp,
        label_download_bp,
        pickup_page_bp,
        pickup_finalize_bp,
        pickup_download_bp,
        customs_page_bp,
        customs_finalize_bp,
        customs_download_bp,
        delivery_page_bp,
        delivery_finalize_bp,
        delivery_download_bp,
    ):
        app.register_blueprint(blueprint)
