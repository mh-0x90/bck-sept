from .. import network
from ..config import internal_context
from .base import StageFlow
from .common import match, number, reference, text
from .end import ShipmentEndStage
from .start import ShipmentStartStage


class ShipmentStages(StageFlow):
    def __init__(self, network_client=network, context_provider=internal_context):
        super().__init__(ShipmentStartStage(), ShipmentEndStage(network_client))
        self.network = network_client
        self.context_provider = context_provider

    STAGE_TITLES = (
        "Shipment overview",
        "Parties",
        "Parcel measurements",
        "Destination",
        "Delivery service",
        "Carrier route",
        "Tracking reference",
        "Final review",
        "Carrier handoff",
        "Final processing",
    )

    STAGE_FIELDS = (
        (("Tracking", "tracking"), ("Status", "kind")),
        (("Sender", "sender"), ("Recipient", "recipient")),
        (("Weight", "weight_kg"), ("Length", "length_cm"), ("Width", "width_cm"), ("Height", "height_cm")),
        (("Destination", "destination"), ("Country", "country"), ("Postal code", "postal_code")),
        (("Service", "service"), ("Weight", "weight_kg")),
        (("Carrier", "carrier"), ("Service", "service")),
        (("Tracking", "tracking"), ("Carrier", "carrier")),
        (("Recipient", "recipient"), ("Destination", "destination"), ("Service", "service"), ("Carrier", "carrier")),
        (("Carrier", "carrier"), ("Tracking", "tracking")),
        (("Tracking", "tracking"),),
    )

    def stage_2(self, record_2, repo):
        text(record_2["payload"], "sender", 2, 80)
        text(record_2["payload"], "recipient", 2, 80)

    def stage_3(self, record_3, repo):
        payload = record_3["payload"]
        number(payload, "weight_kg", 0.01, 100)
        number(payload, "length_cm", 1, 200)
        number(payload, "width_cm", 1, 200)
        number(payload, "height_cm", 1, 200)

    def stage_4(self, record_4, repo):
        payload = record_4["payload"]
        text(payload, "destination", 2, 100)
        reference(repo, "country", payload.get("country"))
        match(payload, "postal_code", r"[A-Z0-9 -]{3,12}")

    def stage_5(self, record_5, repo):
        payload = record_5["payload"]
        service = reference(repo, "service", payload.get("service"))
        meta = repo.reference_meta("service", service) or {}
        limit = meta.get("max_weight")
        if not isinstance(limit, (int, float)) or number(payload, "weight_kg", 0.01, limit) > limit:
            raise ValueError("Service weight limit exceeded")

    def stage_6(self, record_6, repo):
        payload = record_6["payload"]
        carrier = reference(repo, "carrier", payload.get("carrier"))
        service = reference(repo, "service", payload.get("service"))
        reference(repo, "service_carrier", f"{service}:{carrier}")

    def stage_7(self, record_7, repo):
        match(record_7["payload"], "tracking", r"[A-Z0-9-]{6,30}")

    def stage_8(self, record_8, repo):
        payload = record_8["payload"]
        if payload.get("tracking") == payload.get("postal_code"):
            raise ValueError("Shipment references are inconsistent")
        text(payload, "recipient", 2, 80)
        reference(repo, "carrier", payload.get("carrier"))

    def stage_9(self, record_9, repo):
        url, note = self.context_provider()
        record_9["payload"]["internal_url"] = url
        record_9["payload"]["internal_note"] = note
        repo.save_payload(record_9["id"], record_9["payload"], stage=10, status="finalizing")
        record_9["stage"] = 10
        record_9["status"] = "finalizing"
        return record_9




FLOW = ShipmentStages()
