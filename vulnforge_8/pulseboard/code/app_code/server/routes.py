from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app_code.content.service import IntegrationHealthService
from app_code.server.schemas import CheckBody, CheckResponse


router = APIRouter()
service = IntegrationHealthService()
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"


@router.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@router.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@router.post("/api/integrations/check", response_model=CheckResponse)
async def check_integrations(body: CheckBody) -> CheckResponse:
    try:
        await service.refresh(body.filter, body.id_filter)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CheckResponse(status="processed")
