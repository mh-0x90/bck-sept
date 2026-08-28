from __future__ import annotations

from urllib.parse import urlsplit

from .common import PolicyError, require_max_args


_ALLOWED_HOST = "127.0.0.1"
_ALLOWED_NO_VALUE_OPTIONS = {"-s", "--silent", "-S", "--show-error"}
_CONFIG_OPTIONS = {"-K", "--config"}


def _validate_direct_url(value: str) -> None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise PolicyError("invalid curl URL") from exc

    if parsed.scheme != "http":
        raise PolicyError("curl scheme is not allowed")
    if parsed.hostname != _ALLOWED_HOST:
        raise PolicyError("curl destination is not allowed")
    if port not in {None, 80}:
        raise PolicyError("curl port is not allowed")
    if parsed.username is not None or parsed.password is not None:
        raise PolicyError("curl credentials are not allowed")


def validate(args: list[str]) -> None:
    require_max_args(args, 8)

    saw_source = False
    index = 0

    while index < len(args):
        value = args[index]

        if value in _ALLOWED_NO_VALUE_OPTIONS:
            index += 1
            continue

        if value in _CONFIG_OPTIONS:
            if index + 1 >= len(args) or args[index + 1] != "-":
                raise PolicyError("curl config must come from stdin")
            saw_source = True
            index += 2
            continue

        if value.startswith("-"):
            raise PolicyError("unsupported curl option")

        _validate_direct_url(value)
        saw_source = True
        index += 1

    if not saw_source:
        raise PolicyError("curl target is required")
