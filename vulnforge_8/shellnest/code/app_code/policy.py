from __future__ import annotations

import shlex

from .command_validation import PolicyError, validate_stage


MAX_COMMAND_LENGTH = 512
MAX_PIPELINE_STAGES = 6
MAX_TOKEN_LENGTH = 256
DISALLOWED_INPUT = (";", "&&", "||", "&", ">", "<", "`", "$(", "\n", "\r", "\0")


def parse_pipeline(line: str) -> list[list[str]]:
    if not isinstance(line, str) or not line.strip():
        raise PolicyError("command is required")
    if len(line) > MAX_COMMAND_LENGTH:
        raise PolicyError("command is too long")

    for value in DISALLOWED_INPUT:
        if value in line:
            raise PolicyError("unsupported input")

    lexer = shlex.shlex(line, posix=True, punctuation_chars="|")
    lexer.whitespace_split = True
    lexer.commenters = ""
    tokens = list(lexer)

    pipeline: list[list[str]] = []
    current: list[str] = []

    for token in tokens:
        if len(token) > MAX_TOKEN_LENGTH:
            raise PolicyError("token is too long")

        if token == "|":
            if not current:
                raise PolicyError("incomplete pipeline")
            pipeline.append(current)
            current = []
        elif "|" in token:
            raise PolicyError("unsupported operator")
        else:
            current.append(token)

    if not current:
        raise PolicyError("incomplete pipeline")

    pipeline.append(current)

    if len(pipeline) > MAX_PIPELINE_STAGES:
        raise PolicyError("pipeline is too long")

    return pipeline


def validate_proxy_command(line: str) -> list[list[str]]:
    pipeline = parse_pipeline(line)

    for stage in pipeline:
        validate_stage(stage)

    return pipeline
