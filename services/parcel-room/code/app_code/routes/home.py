from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..services.guard import new_csrf_token
from ..services.intake import recent
from ..services.processor import processed_result
from ..view import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def home(request: Request, processed: int | None = None):
    token = request.cookies.get("parcel_csrf") or new_csrf_token()
    result = processed_result(processed) if processed else None
    response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"rows": recent(), "csrf_token": token, "result": result},
    )
    response.set_cookie("parcel_csrf", token, httponly=True, samesite="strict", max_age=3600)
    return response
