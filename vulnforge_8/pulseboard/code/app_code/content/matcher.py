from app_code.content.models import Integration


def filter_by_partial_id(
    items: list[Integration],
    value: str,
) -> list[Integration]:
    if not value:
        return items
    return [item for item in items if value in str(item.record_id)]
