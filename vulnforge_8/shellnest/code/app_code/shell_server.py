from __future__ import annotations

import os
import shlex
import shutil
import socketserver
import subprocess
from pathlib import Path

from .command_validation import PolicyError, validate_stage
from .protocol import MAX_MESSAGE_BYTES, decode_message, encode_message


SERVER_COMMANDS = {"base64", "cat", "curl", "echo"}
MAX_OUTPUT_BYTES = 256 * 1024
COMMAND_TIMEOUT_SECONDS = 3
SERVER_MAX_PIPELINE_STAGES = 6
SERVER_MAX_ARGS_PER_STAGE = 16


class CommandError(Exception):
    pass


def _parse_pipeline(line: str) -> list[list[str]]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars="|")
    lexer.whitespace_split = True
    lexer.commenters = ""
    tokens = list(lexer)

    pipeline: list[list[str]] = []
    current: list[str] = []

    for token in tokens:
        if token == "|":
            if not current:
                raise CommandError("incomplete pipeline")
            pipeline.append(current)
            current = []
        elif "|" in token:
            raise CommandError("unsupported operator")
        else:
            current.append(token)

    if not current:
        raise CommandError("incomplete pipeline")

    pipeline.append(current)

    if len(pipeline) > SERVER_MAX_PIPELINE_STAGES:
        raise CommandError("pipeline is too long")
    if any(len(stage) - 1 > SERVER_MAX_ARGS_PER_STAGE for stage in pipeline):
        raise CommandError("too many arguments")

    return pipeline


def _workspace_path(workspace: Path, raw: str) -> str:
    candidate = Path(raw)

    if candidate.is_absolute():
        raise CommandError("absolute paths are not allowed")

    target = (workspace / candidate).resolve()

    try:
        target.relative_to(workspace.resolve())
    except ValueError as exc:
        raise CommandError("path is outside the workspace") from exc

    return str(target)


def _binary(name: str) -> str:
    path = shutil.which(name)

    if not path:
        raise CommandError(f"{name} is unavailable")

    return path


def _prepare(workspace: Path, parts: list[str]) -> list[str]:
    name, *args = parts

    if name not in SERVER_COMMANDS:
        raise CommandError("command is unavailable")

    try:
        validate_stage(parts)
    except PolicyError as exc:
        raise CommandError(str(exc)) from exc

    if name == "cat":
        if not args:
            return [_binary("cat")]

        return [_binary("cat"), *(_workspace_path(workspace, arg) for arg in args)]

    if name == "base64":
        normalized = ["-d" if arg == "--decode" else arg for arg in args]
        return [_binary("base64"), *normalized]

    return [_binary(name), *args]


def _run_binary(
    workspace: Path,
    parts: list[str],
    stdin_data: bytes | None,
) -> tuple[int, bytes, bytes]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HOME": str(workspace),
    }

    try:
        result = subprocess.run(
            _prepare(workspace, parts),
            cwd=workspace,
            input=stdin_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandError("command timed out") from exc
    except OSError as exc:
        raise CommandError("command could not be started") from exc

    return (
        result.returncode,
        result.stdout[:MAX_OUTPUT_BYTES],
        result.stderr[:MAX_OUTPUT_BYTES],
    )


def run_pipeline(workspace: Path, line: str) -> dict:
    stages = _parse_pipeline(line)
    stdin_data: bytes | None = None
    stderr_parts: list[bytes] = []
    return_code = 0

    for stage in stages:
        return_code, stdout, stderr = _run_binary(workspace, stage, stdin_data)
        stdin_data = stdout

        if stderr:
            stderr_parts.append(stderr)

    return {
        "code": return_code,
        "stdout": (stdin_data or b"").decode("utf-8", errors="replace"),
        "stderr": b"".join(stderr_parts).decode("utf-8", errors="replace"),
    }


class RequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(MAX_MESSAGE_BYTES + 1)

        try:
            request = decode_message(raw)
            line = request.get("line")

            if not isinstance(line, str):
                raise CommandError("invalid command")

            response = {"ok": True, **run_pipeline(self.server.workspace, line)}
        except (ValueError, CommandError) as exc:
            response = {"ok": False, "error": str(exc)}

        self.wfile.write(encode_message(response))


class ShellServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], workspace: Path):
        self.workspace = workspace.resolve()
        super().__init__(address, RequestHandler)
