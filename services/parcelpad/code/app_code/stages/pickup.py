from .base import StageFlow
from .common import clock, integer, reference, text
from .end import PickupEndStage
from .start import PickupStartStage


class PickupStages(StageFlow):
    def __init__(self):
        super().__init__(PickupStartStage(), PickupEndStage())

    STAGE_TITLES = (
        "Pickup overview",
        "Collection contact",
        "Collection location",
        "Pickup window",
        "Parcel count",
        "Service",
        "Carrier",
        "Booking review",
        "Dispatch handoff",
        "Booked",
    )

    STAGE_FIELDS = (
        (("Pickup", "pickup_ref"),),
        (("Contact", "contact"),),
        (("Location", "location"),),
        (("From", "window_start"), ("To", "window_end")),
        (("Parcels", "parcel_count"),),
        (("Service", "service"),),
        (("Carrier", "carrier"),),
        (("Contact", "contact"), ("Window", "window_start"), ("Parcels", "parcel_count")),
        (("Carrier", "carrier"), ("Location", "location")),
        (("Pickup", "pickup_ref"),),
    )

    def stage_2(self, record_2, repo):
        text(record_2["payload"], "contact", 2, 80)

    def stage_3(self, record_3, repo):
        text(record_3["payload"], "location", 4, 120)

    def stage_4(self, record_4, repo):
        payload = record_4["payload"]
        start = clock(payload, "window_start")
        end = clock(payload, "window_end")
        if start >= end:
            raise ValueError("Pickup window is invalid")

    def stage_5(self, record_5, repo):
        integer(record_5["payload"], "parcel_count", 1, 100)

    def stage_6(self, record_6, repo):
        reference(repo, "service", record_6["payload"].get("service"))

    def stage_7(self, record_7, repo):
        reference(repo, "carrier", record_7["payload"].get("carrier"))

    def stage_8(self, record_8, repo):
        payload = record_8["payload"]
        reference(repo, "service_carrier", f"{payload.get('service')}:{payload.get('carrier')}")
        integer(payload, "parcel_count", 1, 100)

    def stage_9(self, record_9, repo):
        text(record_9["payload"], "location", 4, 120)
        repo.set_stage(record_9["id"], 10, "finalizing")
        record_9["stage"] = 10
        record_9["status"] = "finalizing"




FLOW = PickupStages()
