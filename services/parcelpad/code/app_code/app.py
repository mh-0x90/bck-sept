from flask import Flask

from .config import load_settings
from .csrf import csrf_token
from .routes import register_routes


def create_app():
    settings = load_settings()
    app = Flask(__name__)
    app.secret_key = settings.app_secret
    app.config.update(
        MAX_CONTENT_LENGTH=64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.cookie_secure,
        AUTH_USERNAME=settings.login_username,
        AUTH_PASSWORD=settings.login_password,
    )
    app.jinja_env.autoescape = True
    app.jinja_env.globals["csrf_token"] = csrf_token
    register_routes(app)

    @app.after_request
    def secure_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    return app
