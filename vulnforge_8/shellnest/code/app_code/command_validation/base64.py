from __future__ import annotations

from .common import PolicyError, require_max_args


_ALLOWED_OPTIONS = {"-d", "--decode"}


def validate(args: list[str]) -> None:
    require_max_args(args, 1)

    if any(arg not in _ALLOWED_OPTIONS for arg in args):
        raise PolicyError("unsupported base64 arguments")
