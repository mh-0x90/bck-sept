from flask import Blueprint, redirect, session, url_for

from ..auth import login_required
from ..csrf import require_csrf


bp = Blueprint("logout", __name__)


@bp.post("/logout")
@login_required
@require_csrf
def logout():
    session.clear()
    return redirect(url_for("login.login"))
