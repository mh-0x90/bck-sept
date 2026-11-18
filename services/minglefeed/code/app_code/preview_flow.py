from config import BLOCKED_PREVIEW_HOSTS
from validation import parse_http_url


def validate_preview_url(value):
    value, parsed = parse_http_url(value, "Preview URL")
    if not value:
        return ""
    if parsed.hostname.lower() in BLOCKED_PREVIEW_HOSTS:
        raise ValueError("That preview destination is not allowed.")
    return value
