from app_code.content.models import Integration


def sort_candidates(items: list[Integration]) -> list[Integration]:
    return sorted(items, key=lambda item: (item.priority, item.record_id))
