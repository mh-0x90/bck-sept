from dataclasses import dataclass


@dataclass(frozen=True)
class QueryPlan:
    statement: str
