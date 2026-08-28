from functools import wraps
import hmac
import secrets

from flask import abort, request, session


def csrf_token():
    token = session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def require_csrf(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            supplied = request.form.get("csrf_token", "")
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                abort(400)
        return view(*args, **kwargs)

    return wrapped
