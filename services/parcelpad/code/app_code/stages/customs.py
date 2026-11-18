from decimal import Decimal

from .base import StageFlow
from .common import match, number, reference, text
from .end import CustomsEndStage
from .start import CustomsStartStage


class CustomsStages(StageFlow):
    def __init__(self):
        super().__init__(CustomsStartStage(), CustomsEndStage())

    STAGE_TITLES = (
        "Declaration overview",
        "Exporter",
        "Importer",
        "Destination",
        "Currency",
        "Declared items",
        "Classification",
        "Value review",
        "Submission handoff",
        "Submitted",
    )

    STAGE_FIELDS = (
        (("Declaration", "declaration_ref"),),
        (("Exporter", "exporter"),),
        (("Importer", "importer"),),
        (("Country", "destination_country"),),
        (("Currency", "currency"),),
        (("Items", "items"),),
        (("Items", "items"),),
        (("Declared total", "total_value"), ("Currency", "currency")),
        (("Declaration", "declaration_ref"), ("Country", "destination_country")),
        (("Declaration", "declaration_ref"),),
    )

    def stage_2(self, record_2, repo):
        text(record_2["payload"], "exporter", 2, 100)

    def stage_3(self, record_3, repo):
        text(record_3["payload"], "importer", 2, 100)

    def stage_4(self, record_4, repo):
        reference(repo, "country", record_4["payload"].get("destination_country"))

    def stage_5(self, record_5, repo):
        reference(repo, "currency", record_5["payload"].get("currency"))

    def stage_6(self, record_6, repo):
        items = record_6["payload"].get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 20:
            raise ValueError("Invalid declared items")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Invalid declared item")
            text(item, "description", 2, 100)
            number(item, "quantity", 1, 1000)
            number(item, "unit_value", 0.01, 100000)

    def stage_7(self, record_7, repo):
        for item in record_7["payload"].get("items", []):
            match(item, "hs_code", r"[0-9]{6,10}")

    def stage_8(self, record_8, repo):
        payload = record_8["payload"]
        expected = sum(
            Decimal(str(item["quantity"])) * Decimal(str(item["unit_value"]))
            for item in payload.get("items", [])
        )
        actual = number(payload, "total_value", 0.01, 1000000)
        if expected.quantize(Decimal("0.01")) != actual.quantize(Decimal("0.01")):
            raise ValueError("Declared total does not match items")

    def stage_9(self, record_9, repo):
        reference(repo, "country", record_9["payload"].get("destination_country"))
        repo.set_stage(record_9["id"], 10, "finalizing")
        record_9["stage"] = 10
        record_9["status"] = "finalizing"




FLOW = CustomsStages()
