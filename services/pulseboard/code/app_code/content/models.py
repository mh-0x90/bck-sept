from dataclasses import dataclass


@dataclass(frozen=True)
class FilterRule:
    field: str
    operator: str
    value: str


@dataclass(frozen=True)
class Integration:
    record_id: int
    display_name: str
    region_code: str
    priority: int
    health_url: str


@dataclass(frozen=True)
class RefreshResult:
    candidates: int
    available: int
    matched: int
