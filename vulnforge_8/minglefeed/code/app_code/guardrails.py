import threading
import time
from collections import defaultdict, deque
from http.server import ThreadingHTTPServer

from config import MAX_HTTP_WORKERS, POST_RATE_COUNT, POST_RATE_WINDOW


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args, max_workers=MAX_HTTP_WORKERS, **kwargs):
        self._slots = threading.BoundedSemaphore(max_workers)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        self._slots.acquire()
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


class RateLimiter:
    def __init__(self, count=POST_RATE_COUNT, window=POST_RATE_WINDOW):
        self.count = count
        self.window = window
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key):
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= self.count:
                return False
            events.append(now)
            if not events:
                self._events.pop(key, None)
            return True
