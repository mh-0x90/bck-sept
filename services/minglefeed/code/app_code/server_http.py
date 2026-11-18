from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

from config import INTERNAL_PORT, PREVIEW_REDIRECT_LIMIT

INTERNAL_BASE_URL = f"http://127.0.0.1:{INTERNAL_PORT}/"


def internal_url(path, query=""):
    url = urljoin(INTERNAL_BASE_URL, path.lstrip("/"))
    return f"{url}?{query}" if query else url


def _headers_for(accept):
    return {
        "User-Agent": "Mozilla/5.0 (compatible; MingleFeed/1.0)",
        "Accept": accept,
    }


class ServerRedirects(HTTPRedirectHandler):
    def __init__(self, accept, limit=PREVIEW_REDIRECT_LIMIT):
        self.accept = accept
        self.limit = limit
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > self.limit:
            return None
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        for container in (redirected.headers, redirected.unredirected_hdrs):
            for key in list(container):
                if key.lower() in {"user-agent", "accept"}:
                    container.pop(key, None)
        for key, value in _headers_for(self.accept).items():
            redirected.add_unredirected_header(key, value)
        return redirected


def open_server_url(url, *, accept="*/*", timeout=5, redirect_limit=PREVIEW_REDIRECT_LIMIT):
    request = Request(url, headers=_headers_for(accept))
    opener = build_opener(ServerRedirects(accept, redirect_limit))
    return opener.open(request, timeout=timeout)
