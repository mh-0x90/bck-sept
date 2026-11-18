from datetime import date

from .base import StageFlow
from .common import match, reference, text
from .end import DeliveryEndStage
from .start import DeliveryStartStage


class DeliveryStages(StageFlow):
    def __init__(self):
        super().__init__(DeliveryStartStage(), DeliveryEndStage())

    STAGE_TITLES = (
        "Delivery overview",
        "Shipment reference",
        "Recipient",
        "Delivery location",
        "Handoff method",
        "Carrier",
        "Delivery date",
        "Proof review",
        "Delivery handoff",
        "Confirmed",
    )

    STAGE_FIELDS = (
        (("Tracking", "tracking"),),
        (("Tracking", "tracking"),),
        (("Recipient", "recipient"),),
        (("Location", "location"), ("Type", "location_type")),
        (("Method", "method"),),
        (("Carrier", "carrier"),),
        (("Delivered on", "delivered_on"),),
        (("Proof", "proof_ref"), ("Recipient", "recipient")),
        (("Method", "method"), ("Location", "location")),
        (("Proof", "proof_ref"),),
    )

    def stage_2(self, record_2, repo):
        match(record_2["payload"], "tracking", r"[A-Z0-9-]{6,30}")

    def stage_3(self, record_3, repo):
        text(record_3["payload"], "recipient", 2, 80)

    def stage_4(self, record_4, repo):
        payload = record_4["payload"]
        text(payload, "location", 4, 120)
        reference(repo, "location_type", payload.get("location_type"))

    def stage_5(self, record_5, repo):
        reference(repo, "handoff_method", record_5["payload"].get("method"))

    def stage_6(self, record_6, repo):
        reference(repo, "carrier", record_6["payload"].get("carrier"))

    def stage_7(self, record_7, repo):
        raw = text(record_7["payload"], "delivered_on", 10, 10)
        try:
            date.fromisoformat(raw)
        except ValueError:
            raise ValueError("Invalid delivery date") from None

    def stage_8(self, record_8, repo):
        payload = record_8["payload"]
        match(payload, "proof_ref", r"[A-Z0-9-]{6,30}")
        reference(repo, "handoff_location", f"{payload.get('method')}:{payload.get('location_type')}")

    def stage_9(self, record_9, repo):
        text(record_9["payload"], "recipient", 2, 80)
        repo.set_stage(record_9["id"], 10, "finalizing")
        record_9["stage"] = 10
        record_9["status"] = "finalizing"




FLOW = DeliveryStages()
