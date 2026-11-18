import re
from datetime import time
from decimal import Decimal, InvalidOperation


def require_kind(payload, expected):
    if payload.get("kind") != expected:
        raise ValueError("Unexpected record type")


def text(payload, key, minimum=1, maximum=120):
    value = payload.get(key)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f"Invalid {key}")
    return value.strip()


def match(payload, key, pattern):
    value = text(payload, key)
    if re.fullmatch(pattern, value) is None:
        raise ValueError(f"Invalid {key}")
    return value


def number(payload, key, minimum, maximum):
    value = payload.get(key)
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid {key}") from None
    if parsed < Decimal(str(minimum)) or parsed > Decimal(str(maximum)):
        raise ValueError(f"Invalid {key}")
    return parsed


def integer(payload, key, minimum, maximum):
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"Invalid {key}")
    return value


def reference(repo, category, value):
    if not isinstance(value, str) or not repo.reference_exists(category, value):
        raise ValueError(f"Unsupported {category}")
    return value


def clock(payload, key):
    raw = text(payload, key, 5, 5)
    try:
        hour, minute = (int(part) for part in raw.split(":"))
        parsed = time(hour=hour, minute=minute)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {key}") from None
    return parsed


def display_fields(payload, fields):
    result = []
    for label, key in fields:
        value = payload.get(key, "")
        if isinstance(value, list):
            value = f"{len(value)} item(s)"
        result.append((label, value))
    return result
