from .action import StageAction
from .common import match, require_kind


class ShipmentStartStage(StageAction):
    def execute(self, record_1, repo):
        require_kind(record_1["payload"], "Shipment")


class LabelStartStage(StageAction):
    def execute(self, record_1, repo):
        require_kind(record_1["payload"], "Shipping label")


class PickupStartStage(StageAction):
    def execute(self, record_1, repo):
        require_kind(record_1["payload"], "Pickup booking")
        match(record_1["payload"], "pickup_ref", r"[A-Z0-9-]{6,30}")


class CustomsStartStage(StageAction):
    def execute(self, record_1, repo):
        require_kind(record_1["payload"], "Customs declaration")
        match(record_1["payload"], "declaration_ref", r"[A-Z0-9-]{6,30}")


class DeliveryStartStage(StageAction):
    def execute(self, record_1, repo):
        require_kind(record_1["payload"], "Delivery confirmation")
