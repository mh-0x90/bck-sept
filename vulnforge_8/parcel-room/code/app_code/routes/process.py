from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from ..services.guard import check_csrf, check_rate
from ..services.processor import process_parcel, receipt_for_download

router = APIRouter()


@router.post("/process/{parcel_id}")
def process(parcel_id: int, request: Request, csrf_token: str = Form(...)):
    check_rate(request)
    check_csrf(request, csrf_token)
    try:
        result = process_parcel(parcel_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "Parcel not found")
    return RedirectResponse(f"/?processed={parcel_id}", status_code=303)


@router.get("/receipts/{temp_file_name}/download")
def download_receipt(temp_file_name: str, request: Request):
    check_rate(request)
    path = receipt_for_download(temp_file_name)
    if path is None:
        raise HTTPException(404, "Receipt not found")
    return FileResponse(path, media_type="text/plain", filename=path.name)
