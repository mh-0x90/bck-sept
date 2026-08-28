import json
from functools import wraps
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

from action_flow import account_action
from config import INTERNAL_PORT, REQUEST_TIMEOUT
from file_flow import read_private_file
from guardrails import BoundedThreadingHTTPServer

LOOPBACK_PEERS = {"127.0.0.1", "::1"}


def require_internal_peer(handler):
    @wraps(handler)
    def wrapped(self, *args, **kwargs):
        if not self.client_address or self.client_address[0] not in LOOPBACK_PEERS:
            self._json(403, {"error": "internal access only"})
            return
        return handler(self, *args, **kwargs)

    return wrapped


class InternalHandler(BaseHTTPRequestHandler):
    server_version = "Accounts/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT)

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if body:
            self.wfile.write(body)

    @require_internal_peer
    def do_GET(self):
        parsed = urlsplit(self.path)

        if parsed.path == "/health":
            self._json(200, {"service": "accounts", "status": "ok"})
            return

        if parsed.path.startswith("/files/"):
            status, body, content_type = read_private_file(parsed.path)
            if status == 404:
                self._json(404, {"error": "not found"})
            elif status == 413:
                self._json(413, {"error": "file too large"})
            else:
                self._bytes(status, body, content_type)
            return

        if parsed.path == "/actions/account":
            status, payload = account_action(parsed.query)
            self._json(status, payload)
            return

        self._json(404, {"error": "not found"})

    def log_message(self, _format, *_args):
        return


def start_internal_service():
    server = BoundedThreadingHTTPServer(("127.0.0.1", INTERNAL_PORT), InternalHandler, max_workers=8)
    thread = __import__("threading").Thread(
        target=server.serve_forever, name="account-service", daemon=True
    )
    thread.start()
    return server
