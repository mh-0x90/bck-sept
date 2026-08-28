from .base import StageFlow
from .common import match, reference
from .end import LabelEndStage
from .start import LabelStartStage


class LabelStages(StageFlow):
    def __init__(self):
        super().__init__(LabelStartStage(), LabelEndStage())

    STAGE_TITLES = (
        "Label overview",
        "Shipment link",
        "Label format",
        "Carrier",
        "Delivery service",
        "Tracking",
        "Route code",
        "Label review",
        "Publishing check",
        "Published",
    )

    STAGE_FIELDS = (
        (("Label", "kind"), ("Shipment", "shipment_ref")),
        (("Shipment", "shipment_ref"),),
        (("Format", "format"),),
        (("Carrier", "carrier"),),
        (("Service", "service"),),
        (("Tracking", "tracking"),),
        (("Route", "route_code"),),
        (("Format", "format"), ("Carrier", "carrier"), ("Route", "route_code")),
        (("Shipment", "shipment_ref"), ("Tracking", "tracking")),
        (("Tracking", "tracking"),),
    )

    def stage_2(self, record_2, repo):
        match(record_2["payload"], "shipment_ref", r"[A-Z0-9-]{6,30}")

    def stage_3(self, record_3, repo):
        reference(repo, "label_format", record_3["payload"].get("format"))

    def stage_4(self, record_4, repo):
        reference(repo, "carrier", record_4["payload"].get("carrier"))

    def stage_5(self, record_5, repo):
        reference(repo, "service", record_5["payload"].get("service"))

    def stage_6(self, record_6, repo):
        match(record_6["payload"], "tracking", r"[A-Z0-9-]{6,30}")

    def stage_7(self, record_7, repo):
        match(record_7["payload"], "route_code", r"[A-Z0-9-]{4,16}")

    def stage_8(self, record_8, repo):
        payload = record_8["payload"]
        reference(repo, "service_carrier", f"{payload.get('service')}:{payload.get('carrier')}")

    def stage_9(self, record_9, repo):
        payload = record_9["payload"]
        if payload.get("shipment_ref") != payload.get("tracking"):
            raise ValueError("Label and shipment references do not match")
        repo.set_stage(record_9["id"], 10, "finalizing")
        record_9["stage"] = 10
        record_9["status"] = "finalizing"




FLOW = LabelStages()
