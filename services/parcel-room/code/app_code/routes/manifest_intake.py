import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from ..services.guard import check_csrf, check_rate, check_request_size
from ..services.intake import store_parcel
from ..services.request_reader import parser_state, read_form, read_manifest

router = APIRouter(prefix="/intake")
@router.post("/manifest")
async def manifest_intake(request: Request):
    check_rate(request)
    check_request_size(request)
    data, token = await read_manifest(request)
    check_csrf(request, token)
    try:
        store_parcel(data, "manifest", parser_state(request))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return RedirectResponse("/", status_code=303)