import hmac
import json
import mimetypes
import secrets
import sqlite3
from http import cookies
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import (
    APP_PORT,
    COOKIE_SECURE,
    MAX_FORM_BYTES,
    REQUEST_TIMEOUT,
)
from db import (
    create_post,
    create_session,
    create_user,
    delete_session,
    get_user_by_name,
    list_posts,
    preview_states,
    user_for_session,
    verify_password,
)
from guardrails import BoundedThreadingHTTPServer, RateLimiter
from preview import enqueue
from server_http import internal_url, open_server_url
from media_flow import media_kind, validate_media_url
from preview_flow import validate_preview_url
from validation import clean_text

BASE = Path(__file__).resolve().parent
_post_limiter = RateLimiter()

TEMPLATES = Environment(
    loader=FileSystemLoader(BASE / "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def render(name, **context):
    return TEMPLATES.get_template(name).render(**context).encode()


class AppHandler(BaseHTTPRequestHandler):
    server_version = "MingleFeed/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT)

    def _cookies(self):
        jar = cookies.SimpleCookie()
        raw = self.headers.get("Cookie")
        if raw:
            jar.load(raw)
        return jar

    def _cookie_value(self, name):
        item = self._cookies().get(name)
        return item.value if item else ""

    def _csrf(self):
        token = self._cookie_value("csrf") or secrets.token_urlsafe(24)
        self._csrf_to_set = token
        return token

    def _set_cookie(self, name, value, http_only=True, max_age=None):
        jar = cookies.SimpleCookie()
        jar[name] = value
        jar[name]["path"] = "/"
        jar[name]["samesite"] = "Lax"
        if http_only:
            jar[name]["httponly"] = True
        if COOKIE_SECURE:
            jar[name]["secure"] = True
        if max_age is not None:
            jar[name]["max-age"] = str(max_age)
        self.send_header("Set-Cookie", jar.output(header="").strip())

    def _headers(self, status=200, content_type="text/html; charset=utf-8", length=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' http: https: data:; media-src 'self' http: https:; "
            "style-src 'self'; script-src 'self'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'",
        )
        if getattr(self, "_csrf_to_set", None):
            self._set_cookie("csrf", self._csrf_to_set, http_only=True)

    def _html(self, body, status=200):
        self._headers(status=status, length=len(body))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _form(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError as exc:
            raise ValueError("Invalid request size.") from exc
        if length < 0 or length > MAX_FORM_BYTES:
            raise OverflowError("Request is too large.")
        raw = self.rfile.read(length).decode("utf-8", "replace")
        values = parse_qs(raw, keep_blank_values=True, max_num_fields=20)
        return {key: vals[-1] for key, vals in values.items()}

    def _check_csrf(self, form):
        cookie = self._cookie_value("csrf")
        token = form.get("_csrf", "")
        return bool(cookie and token and hmac.compare_digest(cookie, token))

    def _current_user(self):
        return user_for_session(self._cookie_value("sid"))

    def _page_context(self, **extra):
        return {"user": self._current_user(), "csrf": self._csrf(), **extra}

    def _static(self, path):
        name = path.removeprefix("/static/")
        if "/" in name or ".." in name:
            self.send_error(404)
            return
        file_path = BASE / "static" / name
        if not file_path.is_file():
            self.send_error(404)
            return
        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self._headers(200, content_type, len(body))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/static/"):
            return self._static(parsed.path)
        if parsed.path == "/":
            posts = [dict(row) for row in list_posts()]
            for post in posts:
                post["media_kind"] = media_kind(post.get("media_url"))
            return self._html(render("feed.html", **self._page_context(posts=posts)))
        if parsed.path == "/login":
            return self._html(render("login.html", **self._page_context(error="")))
        if parsed.path == "/register":
            return self._html(render("register.html", **self._page_context(error="")))
        if parsed.path == "/profile":
            user = self._current_user()
            if not user:
                return self._redirect("/login")
            query = urlencode({"user_id": user["id"]})
            account = None
            try:
                with open_server_url(
                    internal_url("/actions/account", query),
                    accept="application/json",
                    timeout=2,
                    redirect_limit=0,
                ) as response:
                    account = json.loads(response.read(8192))
            except OSError:
                pass
            return self._html(render("profile.html", **self._page_context(account=account)))
        if parsed.path == "/api/previews":
            return self._json(preview_states())
        self.send_error(404)

    def do_POST(self):
        parsed = urlsplit(self.path)
        client_key = self.client_address[0] if self.client_address else "unknown"
        if not _post_limiter.allow(client_key):
            return self._html(render("error.html", message="Too many requests. Try again shortly."), 429)
        try:
            form = self._form()
        except OverflowError:
            self.close_connection = True
            return self._html(render("error.html", message="Request is too large."), 413)
        except ValueError:
            return self._html(render("error.html", message="Invalid request."), 400)
        if not self._check_csrf(form):
            return self._html(render("error.html", message="Request could not be verified."), 400)

        if parsed.path == "/register":
            username = clean_text(form.get("username"), 40)
            password = form.get("password", "")
            if len(username) < 3 or len(password) < 10:
                return self._html(
                    render("register.html", **self._page_context(error="Use a 3+ character name and a 10+ character password.")),
                    400,
                )
            try:
                user_id = create_user(username, password)
            except sqlite3.IntegrityError:
                return self._html(
                    render("register.html", **self._page_context(error="That username is already taken.")),
                    400,
                )
            sid = create_session(user_id)
            self.send_response(303)
            self.send_header("Location", "/")
            self._set_cookie("sid", sid, http_only=True)
            self.end_headers()
            return

        if parsed.path == "/login":
            username = clean_text(form.get("username"), 40)
            password = form.get("password", "")
            user = get_user_by_name(username)
            if not user or not verify_password(password, user["password_hash"]):
                return self._html(
                    render("login.html", **self._page_context(error="Invalid username or password.")),
                    401,
                )
            sid = create_session(user["id"])
            self.send_response(303)
            self.send_header("Location", "/")
            self._set_cookie("sid", sid, http_only=True)
            self.end_headers()
            return

        if parsed.path == "/logout":
            delete_session(self._cookie_value("sid"))
            self.send_response(303)
            self.send_header("Location", "/")
            self._set_cookie("sid", "", http_only=True, max_age=0)
            self.end_headers()
            return

        if parsed.path == "/posts":
            user = self._current_user()
            if not user:
                return self._redirect("/login")
            body = clean_text(form.get("body"), 1000)
            if not body:
                return self._html(render("error.html", message="Post text is required."), 400)
            try:
                media_url = validate_media_url(form.get("media_url"))
                preview_url = validate_preview_url(form.get("preview_url"))
            except ValueError as exc:
                return self._html(render("error.html", message=str(exc)), 400)
            post_id = create_post(user["id"], body, media_url, preview_url)
            if preview_url:
                enqueue(post_id)
            return self._redirect("/")

        self.send_error(404)

    def log_message(self, format, *args):
        print(f"web: {self.address_string()} - {format % args}")


def run_web():
    server = BoundedThreadingHTTPServer(("0.0.0.0", APP_PORT), AppHandler)
    server.serve_forever()
