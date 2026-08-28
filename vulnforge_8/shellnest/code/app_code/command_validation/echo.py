from __future__ import annotations

from .common import PolicyError, require_max_args


def validate(args: list[str]) -> None:
    require_max_args(args, 16)

    if any(arg.startswith("-") for arg in args):
        raise PolicyError("echo options are not supported")
