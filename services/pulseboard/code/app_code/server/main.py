from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app_code.network.probe import ProbeServer
from app_code.server.routes import router
from app_code.storage.database import initialise_database


WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
probe = ProbeServer()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialise_database()
    probe.start()
    try:
        yield
    finally:
        probe.stop()


app = FastAPI(
    title="Pulseboard",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self'; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


app.include_router(router)
app.mount("/assets", StaticFiles(directory=WEB_ROOT / "assets"), name="assets")
