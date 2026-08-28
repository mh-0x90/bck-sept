import hashlib
import hmac
import os
import re
import secrets
import smtplib
import sqlite3
import time
from email.message import EmailMessage
from http import cookies
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, quote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from db import (
    create_user,
    get_team_name,
    list_teams,
    login_user,
    rename_team,
    team_filter,
    user_by_id,
)

HERE = os.path.dirname(os.path.abspath(__file__))

SMTP_HOST = os.environ.get("SMTP_HOST", "127.0.0.1")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))

SECRET = (
    os.environ.get("APP_SECRET")
    or secrets.token_urlsafe(48)
).encode()

COMPANY_DOMAIN = "apple.test"

USERNAME_RE = re.compile(
    r"^[A-Za-z0-9_]{3,32}$"
)

TEMPLATES = Environment(
    loader=FileSystemLoader(
        os.path.join(HERE, "templates")
    ),
    autoescape=select_autoescape(
        ("html", "xml")
    ),
)


def make_company_email(name):
    return f"{name}@{COMPANY_DOMAIN}"


def sign(value):
    return hmac.new(
        SECRET,
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


def make_session(user_id):
    raw = str(user_id)

    return (
        f"{raw}."
        f"{sign('session:' + raw)}"
    )


def read_session(value):
    if not value or "." not in value:
        return None

    raw, signature = value.split(".", 1)

    if not raw.isdigit():
        return None

    expected = sign(
        "session:" + raw
    )

    if not hmac.compare_digest(
        signature,
        expected,
    ):
        return None

    return int(raw)


def send_mail(
    recipient,
    subject,
    body,
):
    message = EmailMessage()

    message["From"] = (
        f"hello@{COMPANY_DOMAIN}"
    )

    message["To"] = recipient
    message["Subject"] = subject

    message.set_content(body)

    last_error = None

    for _ in range(8):
        try:
            with smtplib.SMTP(
                SMTP_HOST,
                SMTP_PORT,
                timeout=2,
            ) as smtp:
                smtp.send_message(
                    message
                )

            return

        except OSError as exc:
            last_error = exc
            time.sleep(0.15)

    if last_error:
        raise last_error


class Handler(
    BaseHTTPRequestHandler
):
    server_version = "CompanyEmail"

    def cookie_jar(self):
        jar = cookies.SimpleCookie()

        jar.load(
            self.headers.get(
                "Cookie",
                "",
            )
        )

        return jar

    def current_user(self):
        jar = self.cookie_jar()

        token = jar.get(
            "companyemail_session"
        )

        value = (
            token.value
            if token
            else None
        )

        user_id = read_session(
            value
        )

        return user_by_id(
            user_id
        )

    def csrf_token(self):
        jar = self.cookie_jar()

        item = jar.get(
            "companyemail_csrf"
        )

        if (
            item
            and len(item.value) >= 32
        ):
            return (
                item.value,
                False,
            )

        return (
            secrets.token_urlsafe(32),
            True,
        )

    def valid_csrf(
        self,
        form,
    ):
        jar = self.cookie_jar()

        item = jar.get(
            "companyemail_csrf"
        )

        supplied = form.get(
            "csrf",
            [""],
        )[0]

        if (
            not item
            or not supplied
        ):
            return False

        return hmac.compare_digest(
            item.value,
            supplied,
        )

    def form(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return {}

        if length < 0:
            self.send_error(400, "Invalid Content-Length")
            return {}

        if length > 32768:
            self.send_error(413, "Request body too large")
            return {}

        data = self.rfile.read(length)

        return parse_qs(
            data.decode("utf-8", "replace"),
            keep_blank_values=True,
        )
    
    def send_html(
        self,
        template,
        status=200,
        extra_cookies=None,
        **context,
    ):
        csrf, fresh = (
            self.csrf_token()
        )

        body = (
            TEMPLATES
            .get_template(template)
            .render(
                csrf=csrf,
                domain=COMPANY_DOMAIN,
                **context,
            )
            .encode()
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        self.send_header(
            "Referrer-Policy",
            "same-origin",
        )

        if fresh:
            self.send_header(
                "Set-Cookie",
                (
                    "companyemail_csrf="
                    f"{csrf}; "
                    "Path=/; "
                    "HttpOnly; "
                    "SameSite=Lax"
                ),
            )

        for cookie in (
            extra_cookies or []
        ):
            self.send_header(
                "Set-Cookie",
                cookie,
            )

        self.end_headers()

        self.wfile.write(
            body
        )

    def redirect(
        self,
        location,
        extra_cookies=None,
    ):
        self.send_response(
            303
        )

        self.send_header(
            "Location",
            location,
        )

        for cookie in (
            extra_cookies or []
        ):
            self.send_header(
                "Set-Cookie",
                cookie,
            )

        self.end_headers()

    def do_GET(self):
        parsed = urlparse(
            self.path
        )

        if (
            parsed.path
            == "/static/look.css"
        ):
            css_path = os.path.join(
                HERE,
                "static",
                "look.css",
            )

            with open(
                css_path,
                "rb",
            ) as handle:
                data = handle.read()

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/css; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(data)),
            )

            self.send_header(
                "X-Content-Type-Options",
                "nosniff",
            )

            self.end_headers()

            self.wfile.write(
                data
            )

            return

        if (
            parsed.path
            == "/healthz"
        ):
            data = b'{"ok":true}'

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "application/json",
            )

            self.send_header(
                "Content-Length",
                str(len(data)),
            )

            self.end_headers()

            self.wfile.write(
                data
            )

            return

        user = self.current_user()

        if parsed.path == "/":
            if user:
                self.redirect(
                    "/teams"
                )
            else:
                self.send_html(
                    "welcome.html"
                )

            return

        if (
            parsed.path
            == "/signup"
        ):
            self.send_html(
                "signup.html",
                teams=list_teams(),
                error=None,
            )

            return

        if (
            parsed.path
            == "/login"
        ):
            self.send_html(
                "signin.html",
                error=None,
            )

            return

        if (
            parsed.path
            == "/teams"
        ):
            if not user:
                self.redirect(
                    "/login"
                )

                return

            params = parse_qs(
                parsed.query
            )

            query = params.get(
                "q",
                [""],
            )[0][:120]

            try:
                rows = (
                    team_filter(
                        user["team_id"],
                        query,
                    )
                )

                error = None

            except sqlite3.Error:
                rows = []

                error = (
                    "That filter could "
                    "not be processed."
                )

            note = params.get(
                "note",
                [""],
            )[0]

            message = {
                "welcome":
                    (
                        "Account created "
                        "and signup mail "
                        "captured."
                    ),

                "changed":
                    "Team name changed.",

                "mail-sent":
                    "Local mail captured.",
            }.get(note)

            current_team_name = (
                get_team_name(
                    user["team_id"]
                )
            )

            self.send_html(
                "teams.html",
                user=user,
                rows=rows,
                query=query,
                error=error,
                message=message,
                current_team_name=(
                    current_team_name
                ),
            )

            return

        self.send_error(
            404
        )

    def do_POST(self):
        parsed = urlparse(
            self.path
        )

        form = self.form()

        # Central CSRF check.
        # Every POST passes here first.
        if not self.valid_csrf(
            form
        ):
            self.send_error(
                400,
                "Invalid form token",
            )

            return

        if (
            parsed.path
            == "/signup"
        ):
            self.handle_signup(
                form
            )

            return

        if (
            parsed.path
            == "/login"
        ):
            self.handle_login(
                form
            )

            return

        if (
            parsed.path
            == "/logout"
        ):
            self.redirect(
                "/",
                [
                    (
                        "companyemail_session=; "
                        "Path=/; "
                        "HttpOnly; "
                        "SameSite=Lax; "
                        "Max-Age=0"
                    )
                ],
            )

            return

        if (
            parsed.path
            == "/mail/send"
        ):
            self.handle_send_mail(
                form
            )

            return

        if parsed.path.startswith(
            "/teams/rename/"
        ):
            self.handle_team_rename(
                parsed,
                form,
            )

            return

        self.send_error(
            404
        )

    def handle_signup(
        self,
        form,
    ):
        username = form.get(
            "username",
            [""],
        )[0].strip()

        password = form.get(
            "password",
            [""],
        )[0]

        team_raw = form.get(
            "team_id",
            [""],
        )[0]

        teams = list_teams()

        selected_team = next(
            (
                row
                for row in teams
                if (
                    team_raw.isdigit()
                    and row["id"]
                    == int(team_raw)
                )
            ),
            None,
        )

        user_email = (
            make_company_email(
                username
            )
        )

        team_email = (
            make_company_email(
                selected_team["name"]
            )
            if selected_team
            else None
        )

        error = None

        if not USERNAME_RE.fullmatch(
            username
        ):
            error = (
                "Username must be "
                "3-32 letters, numbers, "
                "or underscores."
            )

        elif not (
            10
            <= len(password)
            <= 128
        ):
            error = (
                "Password must be "
                "10-128 characters."
            )

        elif not selected_team:
            error = (
                "Choose a valid team."
            )

        if error:
            self.send_html(
                "signup.html",
                status=400,
                teams=teams,
                error=error,
            )

            return

        try:
            user_id = create_user(
                username,
                user_email,
                password,
                selected_team["id"],
                team_email,
            )

        except ValueError:
            self.send_html(
                "signup.html",
                status=400,
                teams=teams,
                error=(
                    "Generated company "
                    "email is invalid."
                ),
            )

            return

        except sqlite3.IntegrityError:
            self.send_html(
                "signup.html",
                status=409,
                teams=teams,
                error=(
                    "That username is "
                    "already registered."
                ),
            )

            return

        try:
            send_mail(
                user_email,
                "Welcome to CompanyEmail",
                (
                    f"Hi {username},\n\n"
                    "You joined "
                    f"{selected_team['name']}.\n"
                ),
            )

        except (
            OSError,
            smtplib.SMTPException,
        ):
            pass

        session_cookie = (
            "companyemail_session="
            f"{make_session(user_id)}; "
            "Path=/; "
            "HttpOnly; "
            "SameSite=Lax"
        )

        self.redirect(
            "/teams?note=welcome",
            [session_cookie],
        )

    def handle_login(
        self,
        form,
    ):
        username = form.get(
            "username",
            [""],
        )[0].strip()

        password = form.get(
            "password",
            [""],
        )[0]

        user_id = login_user(
            username,
            password,
        )

        if not user_id:
            self.send_html(
                "signin.html",
                status=401,
                error=(
                    "Invalid username "
                    "or password."
                ),
            )

            return

        session_cookie = (
            "companyemail_session="
            f"{make_session(user_id)}; "
            "Path=/; "
            "HttpOnly; "
            "SameSite=Lax"
        )

        self.redirect(
            "/teams",
            [session_cookie],
        )

    def handle_team_rename(
        self,
        parsed,
        form,
    ):
        user = self.current_user()

        if not user:
            self.redirect(
                "/login"
            )

            return

        try:
            team_id = int(
                parsed.path.rsplit(
                    "/",
                    1,
                )[1]
            )

        except ValueError:
            self.send_error(
                404
            )

            return

        query = form.get(
            "q",
            [""],
        )[0][:120]

        new_name = form.get(
            "new_name",
            [""],
        )[0][:120]

        try:
            allowed = {
                row["id"]
                for row
                in team_filter(
                    user["team_id"],
                    query,
                )
            }

        except sqlite3.Error:
            allowed = set()

        if (
            team_id not in allowed
            or not new_name
        ):
            self.redirect(
                "/teams?q="
                + quote(query)
            )

            return

        try:
            rename_team(
                team_id,
                new_name,
            )

        except sqlite3.IntegrityError:
            self.redirect(
                "/teams?q="
                + quote(query)
            )

            return

        # Rename only.
        # No mail is sent here.
        self.redirect(
            "/teams?note=changed"
        )

    def handle_send_mail(
        self,
        form,
    ):
        user = self.current_user()

        if not user:
            self.redirect(
                "/login"
            )

            return

        body = form.get(
            "body",
            [""],
        )[0]

        if (
            not body.strip()
            or len(body) > 4000
            or "\0" in body
        ):
            self.send_error(
                400,
                "Invalid message body",
            )

            return

        # Read the current name directly
        # from the teams table.
        team_name = get_team_name(
            user["team_id"]
        )

        if not team_name:
            self.send_error(
                404,
                "Team not found",
            )

            return

        recipient = (
            f"{team_name}"
            f"@{COMPANY_DOMAIN}"
        )

        subject = (
            "CompanyEmail message"
        )

        try:
            send_mail(
                recipient,
                subject,
                body,
            )

        except (
            OSError,
            smtplib.SMTPException,
        ):
            self.send_error(
                502,
                "Mail could not be sent",
            )

            return

        self.redirect(
            "/teams?note=mail-sent"
        )

    def log_message(
        self,
        fmt,
        *args,
    ):
        print(
            f"{self.address_string()} "
            f"- {fmt % args}"
        )