import json
from fastapi import HTTPException, Request


def parser_state(request: Request) -> str:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        return "standard"

    return "alternate"


async def read_form(request: Request) -> dict:
    form = await request.form()
    return {str(key): str(value) for key, value in form.multi_items() if key != "csrf_token"}


async def read_manifest(request: Request) -> tuple[dict, str]:
    content_type = request.headers.get("content-type", "")
    upload = await parse_body(request=request)

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        token = str(form.get("csrf_token", ""))

        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(400, "Manifest is required")

        raw = await upload.read(128 * 1024)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
            raise HTTPException(400, "Manifest must contain valid JSON") from exc
    else:
        token = request.cookies.get("parcel_csrf", "")
        data = upload

    if not isinstance(data, dict):
        raise HTTPException(400, "Manifest must contain an object")

    return data, token


async def parse_body(request: Request):
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("manifest")
    else:
        try:
            body = await request.json()
            upload = body.get("manifest", body)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "Manifest must contain valid JSON") from exc

    return upload
