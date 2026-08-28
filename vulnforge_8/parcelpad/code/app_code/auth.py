from functools import wraps
import hmac

from flask import current_app, redirect, session, url_for


def authenticate(username, password):
    expected_username = current_app.config["AUTH_USERNAME"]
    expected_password = current_app.config["AUTH_PASSWORD"]
    return hmac.compare_digest(username, expected_username) and hmac.compare_digest(password, expected_password)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("authenticated") is not True:
            return redirect(url_for("login.login"))
        return view(*args, **kwargs)

    return wrapped
