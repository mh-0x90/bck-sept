from flask import Blueprint, redirect, render_template, request, session, url_for

from ..auth import authenticate
from ..csrf import csrf_token, require_csrf


bp = Blueprint("login", __name__)


@bp.route("/login", methods=["GET", "POST"])
@require_csrf
def login():
    if session.get("authenticated") is True:
        return redirect(url_for("home.home"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if authenticate(username, password):
            session.clear()
            session["authenticated"] = True
            session["username"] = username
            csrf_token()
            return redirect(url_for("home.home"))
        error = "Invalid username or password."

    return render_template("login.html", error=error), 401 if error else 200
