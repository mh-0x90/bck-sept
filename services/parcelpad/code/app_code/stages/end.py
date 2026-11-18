from .action import StageAction


class ShipmentEndStage(StageAction):
    def __init__(self, network_client):
        self.network = network_client

    def execute(self, record_10, repo):
        payload = record_10["payload"]
        ok = False
        try:
            ok = self.network.post_internal(
                payload["internal_url"],
                payload["internal_note"],
                record_10["id"],
                timeout=10,
            )
            return ok
        finally:
            payload.pop("internal_url", None)
            payload.pop("internal_note", None)
            repo.save_payload(
                record_10["id"],
                payload,
                stage=10,
                status="complete" if ok else "delivery_error",
            )


class LabelEndStage(StageAction):
    def execute(self, record_10, repo):
        repo.set_stage(record_10["id"], 10, "complete")
        record_10["status"] = "complete"
        return True


class PickupEndStage(StageAction):
    def execute(self, record_10, repo):
        repo.set_stage(record_10["id"], 10, "complete")
        record_10["status"] = "complete"
        return True


class CustomsEndStage(StageAction):
    def execute(self, record_10, repo):
        repo.set_stage(record_10["id"], 10, "complete")
        record_10["status"] = "complete"
        return True


class DeliveryEndStage(StageAction):
    def execute(self, record_10, repo):
        repo.set_stage(record_10["id"], 10, "complete")
        record_10["status"] = "complete"
        return True
