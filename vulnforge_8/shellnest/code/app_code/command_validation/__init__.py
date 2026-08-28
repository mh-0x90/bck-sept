from __future__ import annotations

from collections.abc import Callable

from . import base64 as base64_validation
from . import cat as cat_validation
from . import curl as curl_validation
from . import echo as echo_validation
from .common import PolicyError


Validator = Callable[[list[str]], None]

COMMAND_VALIDATORS: dict[str, Validator] = {
    "base64": base64_validation.validate,
    "cat": cat_validation.validate,
    "curl": curl_validation.validate,
    "echo": echo_validation.validate,
}


def validate_stage(stage: list[str]) -> None:
    if not stage:
        raise PolicyError("empty command")

    name, *args = stage
    validator = COMMAND_VALIDATORS.get(name)

    if validator is None:
        raise PolicyError("command is not allowed")

    validator(args)
