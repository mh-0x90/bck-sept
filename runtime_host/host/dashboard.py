#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

APPS = (
    ("CompanyEmail", 8101, "Team email workspace", 8025),
    ("Mailbox", 8102, "Local mailbox viewer", None),
    ("MingleFeed", 8103, "Social feed", None),
    ("Parcel Room", 8104, "Parcel intake workspace", None),
    ("ParcelPad", 8105, "Parcel processing workflow", None),
    ("Pulseboard", 8106, "Connector health dashboard", None),
    ("QuickCart", 8107, "Shopping and receipt flow", None),
    ("ShellNest", 8108, "Command workspace", None),
    ("DocumentsMng", 8109, "Document management and export", None),
)

STYLE = r"""
:root{color-scheme:dark;--bg:#07080a;--panel:#0d1014;--panel2:#12161c;--line:#242b34;--text:#f5f7fa;--muted:#9aa5b1;--ok:#98d6b8;--off:#d7a2a2;--accent:#91b9ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}
main{width:min(1120px,calc(100% - 32px));margin:auto;padding:40px 0 56px}header{display:flex;justify-content:space-between;gap:24px;align-items:end;border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:22px}
h1{margin:0;font-size:clamp(2rem,5vw,3.2rem);letter-spacing:-.045em}.eyebrow{margin:0 0 7px;color:var(--accent);text-transform:uppercase;font-size:.7rem;letter-spacing:.12em;font-weight:800}.intro{margin:8px 0 0;color:var(--muted);max-width:700px}
.badge{border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:7px 10px;color:var(--muted);font-size:.72rem;font-weight:750;white-space:nowrap}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.card{border:1px solid var(--line);background:var(--panel);border-radius:15px;padding:18px}.card-main{display:flex;justify-content:space-between;gap:18px;align-items:center;text-decoration:none;color:inherit}.card:hover{background:var(--panel2);border-color:#384555}.card h2{font-size:1rem;margin:0}.card p{font-size:.78rem;margin:5px 0 0;color:var(--muted)}
.right{text-align:right}.status{font-size:.68rem;font-weight:850;text-transform:uppercase;letter-spacing:.06em}.status.ok{color:var(--ok)}.status.off{color:var(--off)}.port{display:block;margin-top:4px;color:#6f7b88;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.68rem}.aux{display:inline-block;margin-top:12px;padding:6px 9px;border:1px solid var(--line);border-radius:8px;color:#c9d8f1;text-decoration:none;font-size:.7rem}.aux:hover{border-color:#42536a;background:#111722}
footer{margin-top:18px;color:#707b87;font-size:.7rem}@media(max-width:720px){header{align-items:flex-start;flex-direction:column}.grid{grid-template-columns:1fr}}
"""


def is_up(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.18):
            return True
    except OSError:
        return False


def request_hostname(host_header: str) -> str:
    host = (host_header or "localhost").strip()
    if host.startswith("["):
        end = host.find("]")
        return host[1:end] if end > 0 else "localhost"
    return host.rsplit(":", 1)[0] if ":" in host else host


class Handler(BaseHTTPRequestHandler):
    server_version = "AppHub/1.0"

    def log_message(self, _format: str, *_args) -> None:
        return

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            body = b'{"ok":true}'
            self._headers(200, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)
            return
        if path != "/":
            body = b"not found"
            self._headers(404, "text/plain; charset=utf-8", len(body))
            self.wfile.write(body)
            return

        hostname = request_hostname(self.headers.get("Host", ""))
        cards = []
        for name, port, description, aux_port in APPS:
            up = is_up(port)
            status = "Running" if up else "Starting"
            status_class = "ok" if up else "off"
            target = f"http://{hostname}:{port}/"
            aux = ""
            if aux_port is not None:
                aux_target = f"http://{hostname}:{aux_port}/"
                aux = f'<a class="aux" href="{html.escape(aux_target, quote=True)}" target="_blank" rel="noopener noreferrer">Open local mail inbox · :{aux_port}</a>'
            cards.append(
                '<article class="card">'
                f'<a class="card-main" href="{html.escape(target, quote=True)}" target="_blank" rel="noopener noreferrer">'
                f'<div><h2>{html.escape(name)}</h2><p>{html.escape(description)}</p></div>'
                f'<div class="right"><span class="status {status_class}">{status}</span><span class="port">:{port}</span></div></a>'
                f'{aux}</article>'
            )
        doc = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Application Hub</title><style>' + STYLE + '</style></head><body><main>'
            '<header><div><p class="eyebrow">Local application suite</p><h1>Application Hub</h1>'
            '<p class="intro">Eight local applications and their required supporting services are started together. Open an application in a new tab.</p></div>'
            '<span class="badge">8 applications</span></header><section class="grid">' + ''.join(cards) +
            '</section><footer>Runtime interface only. Supporting services are kept local to the container unless explicitly published.</footer>'
            '</main></body></html>'
        ).encode("utf-8")
        self._headers(200, "text/html; charset=utf-8", len(doc))
        self.wfile.write(doc)


def main() -> None:
    port = int(os.environ.get("HUB_PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
