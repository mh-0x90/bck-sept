from app_code.adapter.models import QueryPlan
from app_code.adapter.sqlite_dialect import SqliteDialect
from app_code.content.models import FilterRule


class QueryAdapter:
    def __init__(self) -> None:
        self.dialect = SqliteDialect()

    def build(self, rule: FilterRule) -> QueryPlan:
        return QueryPlan(statement=self.dialect.render(rule))
