from flask import Blueprint, render_template, url_for

from ..auth import login_required
from ..repository import Repository


bp = Blueprint("home", __name__)


@bp.get("/")
@login_required
def home():
    endpoint = {
        "shipment": "shipment_page.page",
        "label": "label_page.page",
        "pickup": "pickup_page.page",
        "customs": "customs_page.page",
        "delivery": "delivery_page.page",
    }
    records = Repository().list_records()
    cards = [
        {
            "id": record["id"],
            "flow_type": record["flow_type"],
            "kind": record["payload"].get("kind", record["flow_type"].title()),
            "status": record["status"],
            "href": url_for(endpoint[record["flow_type"]], record_id=record["id"]),
        }
        for record in records
    ]
    return render_template("home.html", cards=cards)
