import ipaddress
import socket
from urllib.parse import urlsplit


def clean_text(value, limit):
    return (value or "").strip()[:limit]


def parse_http_url(value, label):
    value = clean_text(value, 2000)
    if not value:
        return "", None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{label} must be an http or https URL.")
    if parsed.username or parsed.password:
        raise ValueError(f"{label} cannot contain URL credentials.")
    return value, parsed


def resolved_addresses(hostname, port, label="Host"):
    try:
        return {ipaddress.ip_address(hostname)}
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"{label} could not be resolved.") from exc
    addresses = set()
    for info in infos:
        try:
            addresses.add(ipaddress.ip_address(info[4][0]))
        except ValueError:
            continue
    if not addresses:
        raise ValueError(f"{label} could not be resolved.")
    return addresses
