from app_code.adapter.query_adapter import QueryAdapter
from app_code.content.models import FilterRule, Integration
from app_code.storage.database import connect


class IntegrationRepository:
    def __init__(self) -> None:
        self.adapter = QueryAdapter()

    def find(self, rule: FilterRule) -> list[Integration]:
        plan = self.adapter.build(rule)

        with connect() as db:
            rows = db.execute(plan.statement).fetchall()

        return [
            Integration(
                record_id=row["record_id"],
                display_name=row["display_name"],
                region_code=row["region_code"],
                priority=row["priority"],
                health_url=row["health_url"],
            )
            for row in rows
        ]
