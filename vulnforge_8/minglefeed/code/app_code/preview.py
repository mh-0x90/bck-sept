import logging
import mimetypes
import queue
import threading
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from config import (
    PREVIEW_HTML_LIMIT,
    PREVIEW_QUEUE_LIMIT,
    PREVIEW_REDIRECT_LIMIT,
    PREVIEW_TEXT_LIMIT,
    PREVIEW_TIMEOUT,
    PREVIEW_WORKERS,
)
from db import get_preview_target, pending_preview_ids, set_preview
from server_http import open_server_url
from media_flow import safe_preview_image

log = logging.getLogger("minglefeed.preview")
_jobs = queue.Queue(maxsize=PREVIEW_QUEUE_LIMIT)
_seen = set()
_lock = threading.Lock()


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.image = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): v for k, v in attrs if k}
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() != "meta":
            return
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        content = (attrs.get("content") or "").strip()
        if key in {"og:title", "twitter:title"} and content:
            self.title = self.title or content
        elif key in {"description", "og:description", "twitter:description"} and content:
            self.description = self.description or content
        elif key in {"og:image", "twitter:image"} and content:
            self.image = self.image or content

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            text = data.strip()
            if text:
                self.title = text


def enqueue(post_id):
    with _lock:
        if post_id in _seen:
            return True
        _seen.add(post_id)
    try:
        _jobs.put_nowait(post_id)
        return True
    except queue.Full:
        with _lock:
            _seen.discard(post_id)
        set_preview(post_id, status="failed")
        log.warning("preview queue full for post %s", post_id)
        return False


def _finish(post_id):
    with _lock:
        _seen.discard(post_id)


def _classify(content_type, url):
    content_type = (content_type or "").lower()
    if "text/html" in content_type or "application/xhtml" in content_type:
        return "html"
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("text/"):
        return "text"
    if "pdf" in content_type:
        return "pdf"
    if content_type.startswith("video/"):
        return "video"
    if content_type.startswith("audio/"):
        return "audio"
    guessed = mimetypes.guess_type(urlsplit(url).path)[0] or ""
    if guessed.startswith("image/"):
        return "image"
    if guessed == "application/pdf":
        return "pdf"
    if guessed.startswith("video/"):
        return "video"
    if guessed.startswith("audio/"):
        return "audio"
    return "file"


def process(post_id):
    target = get_preview_target(post_id)
    if not target or not target["preview_url"]:
        set_preview(post_id, status="failed")
        return

    preview_url = target["preview_url"]
    set_preview(post_id, status="processing")
    accept = "text/html,application/xhtml+xml,text/plain,image/*,application/pdf,video/*,audio/*;q=0.8,*/*;q=0.5"
    try:
        with open_server_url(
            preview_url,
            accept=accept,
            timeout=PREVIEW_TIMEOUT,
            redirect_limit=PREVIEW_REDIRECT_LIMIT,
        ) as response:
            final_url = response.geturl()
            content_type = response.headers.get_content_type()
            kind = _classify(content_type, final_url)
            title = ""
            description = ""
            image_url = ""

            if kind == "html":
                raw = response.read(PREVIEW_HTML_LIMIT)
                parser = MetadataParser()
                charset = response.headers.get_content_charset() or "utf-8"
                try:
                    text = raw.decode(charset, "replace")
                except LookupError:
                    text = raw.decode("utf-8", "replace")
                parser.feed(text)
                title = parser.title[:160]
                description = parser.description[:320]
                image_url = safe_preview_image(final_url, parser.image)
            elif kind == "image":
                title = "Image preview"
                description = content_type
                image_url = safe_preview_image(final_url, final_url)
            elif kind == "text":
                raw = response.read(PREVIEW_TEXT_LIMIT)
                charset = response.headers.get_content_charset() or "utf-8"
                try:
                    text = raw.decode(charset, "replace")
                except LookupError:
                    text = raw.decode("utf-8", "replace")
                title = "Text preview"
                description = text.strip()[:320]
            else:
                title = f"{kind.capitalize()} preview"
                description = content_type

            set_preview(
                post_id,
                status="ready",
                kind=kind,
                title=title or "Link preview",
                description=description,
                image_url=image_url,
                content_type=content_type,
            )
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        log.info("preview failed for post %s: %s", post_id, exc)
        set_preview(post_id, status="failed")


def worker_loop():
    while True:
        post_id = _jobs.get()
        try:
            process(post_id)
        finally:
            _finish(post_id)
            _jobs.task_done()


def start_worker():
    for index in range(PREVIEW_WORKERS):
        threading.Thread(target=worker_loop, name=f"preview-worker-{index + 1}", daemon=True).start()
    for post_id in pending_preview_ids():
        enqueue(post_id)
