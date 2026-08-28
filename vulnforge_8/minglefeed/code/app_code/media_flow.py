from urllib.parse import urljoin, urlsplit

from validation import parse_http_url, resolved_addresses


def validate_public_media_url(value, label="Media URL"):
    value, parsed = parse_http_url(value, label)
    if not value:
        return ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = resolved_addresses(parsed.hostname, port, label)
    if any(not address.is_global for address in addresses):
        raise ValueError(f"{label} must use a public destination.")
    return value


def validate_media_url(value):
    return validate_public_media_url(value, "Media URL")


def safe_preview_image(base_url, value):
    if not value:
        return ""
    candidate = urljoin(base_url, value.strip())[:2000]
    try:
        return validate_public_media_url(candidate, "Preview image")
    except ValueError:
        return ""


def media_kind(url):
    path = urlsplit(url or "").path.lower()
    if path.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return "image"
    if path.endswith((".mp4", ".webm", ".mov")):
        return "video"
    if path.endswith((".mp3", ".wav", ".ogg", ".m4a")):
        return "audio"
    if path.endswith(".pdf"):
        return "pdf"
    return "link"
