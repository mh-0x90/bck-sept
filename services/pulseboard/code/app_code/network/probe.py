from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class ProbeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/probe/steady":
            self.send_response(204)
        elif self.path == "/probe/slow":
            self.send_response(503)
        else:
            self.send_response(404)
        self.end_headers()

    def log_message(self, *_: object) -> None:
        return


class ProbeServer:
    def __init__(self) -> None:
        self.server: ThreadingHTTPServer | None = None
        self.thread: Thread | None = None

    def start(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 9101), ProbeHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=1)
