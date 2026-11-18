import json
import mimetypes
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .policy import PolicyError, validate_proxy_command
from .protocol import MAX_MESSAGE_BYTES, encode_message

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"


def _proxy_request(host: str, port: int, line: str) -> dict:
    with socket.create_connection((host, port), timeout=4) as connection:
        connection.sendall(encode_message({"line": line}))
        reader = connection.makefile("rb")
        raw = reader.readline(MAX_MESSAGE_BYTES + 1)

    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("invalid server response")
    return value


class ProxyHandler(BaseHTTPRequestHandler):
    shell_host = "127.0.0.1"
    shell_port = 8765
    max_body_bytes = 16 * 1024

    def log_message(self, format: str, *args) -> None:
        return

    def _send_headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        self._send_headers(status, content_type, len(body))
        self.wfile.write(body)

    def _send_json(self, status: int, value: dict) -> None:
        body = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", body)

    def _serve_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return
        body = path.read_bytes()
        guessed = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self._send_bytes(HTTPStatus.OK, guessed, body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._serve_file(TEMPLATE_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/static/style.css":
            self._serve_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            return
        if path == "/static/app.js":
            self._serve_file(STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
            return
        if path == "/api/status":
            try:
                result = _proxy_request(self.shell_host, self.shell_port, "echo ready")
                self._send_json(
                    HTTPStatus.OK if result.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE,
                    {"ok": bool(result.get("ok"))},
                )
            except (OSError, ValueError, json.JSONDecodeError):
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"ok": False, "error": "command server unavailable"},
                )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/run":
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid request"})
            return

        if content_length <= 0 or content_length > self.max_body_bytes:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid request"})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid request"})
            return

        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid request"})
            return

        line = payload.get("command")
        try:
            validate_proxy_command(line)
            result = _proxy_request(self.shell_host, self.shell_port, line)
        except PolicyError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return
        except (OSError, ValueError, json.JSONDecodeError):
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"ok": False, "error": "command server unavailable"},
            )
            return

        self._send_json(
            HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST,
            result,
        )


def make_proxy_server(
    address: tuple[str, int],
    shell_host: str = "127.0.0.1",
    shell_port: int = 8765,
) -> ThreadingHTTPServer:
    handler = type(
        "ConfiguredProxyHandler",
        (ProxyHandler,),
        {"shell_host": shell_host, "shell_port": shell_port},
    )
    return ThreadingHTTPServer(address, handler)
