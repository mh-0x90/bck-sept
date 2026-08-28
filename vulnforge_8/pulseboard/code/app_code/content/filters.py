from app_code.content.models import FilterRule
from app_code.server.schemas import FilterBody


def normalise_filter(raw: FilterBody) -> FilterRule:
    value = raw.value.strip()
    if not value:
        raise ValueError("Invalid region filter")

    return FilterRule(
        field=raw.field,
        operator=raw.operator,
        value=value,
    )


def normalise_id_filter(value: str) -> str:
    clean = value.strip()
    if len(clean) > 12 or (clean and not clean.isdigit()):
        raise ValueError("Invalid identifier filter")
    return clean
