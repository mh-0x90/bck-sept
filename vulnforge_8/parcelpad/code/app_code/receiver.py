from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
import time

from .config import receiver_token


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path != "/internal":
            self.send_error(404)
            return
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {receiver_token()}"
        if not hmac.compare_digest(supplied, expected):
            self.send_error(401)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 4096:
                raise ValueError
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload.get("record_id"), str) or not isinstance(payload.get("note"), str):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            self.send_error(400)
            return
        time.sleep(max(0.0, min(float(os.environ.get("RECEIVER_DELAY", "6")), 9.0)))
        body = b'{"status":"accepted"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()


if __name__ == "__main__":
    main()
