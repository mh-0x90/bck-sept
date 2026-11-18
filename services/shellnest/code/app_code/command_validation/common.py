from __future__ import annotations


class PolicyError(Exception):
    pass


def require_max_args(args: list[str], limit: int) -> None:
    if len(args) > limit:
        raise PolicyError("too many arguments")
