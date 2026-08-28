from __future__ import annotations

from pathlib import PurePosixPath

from .common import PolicyError, require_max_args


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\x00" not in value
    )


def validate(args: list[str]) -> None:
    require_max_args(args, 8)

    for arg in args:
        if arg.startswith("-") or not _safe_relative_path(arg):
            raise PolicyError("unsupported cat argument")
