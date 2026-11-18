import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from ..services.guard import check_csrf, check_rate, check_request_size
from ..services.intake import store_parcel
from ..services.request_reader import parser_state, read_form, read_manifest

router = APIRouter(prefix="/intake")

@router.post("/form")
async def form_intake(request: Request):
    check_rate(request)
    check_request_size(request)
    form = await request.form()
    token = str(form.get("csrf_token", ""))
    check_csrf(request, token)
    fields = {str(key): str(value) for key, value in form.multi_items() if key != "csrf_token"}
    carrier = str(fields.get("carrier", "")).strip()[:80]
    match = re.compile(r"\s*([A-Za-z0-9._-]+)\s*$", re.MULTILINE).search(carrier)
    if match is None:
        raise ValueError("Carrier line not matching")
    carrier = match.group(1)
    try:
        store_parcel(fields, "form", parser_state(request))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return RedirectResponse("/", status_code=303)
