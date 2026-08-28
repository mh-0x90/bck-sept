import secrets
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from ..config import MAX_REQUEST_BYTES, RATE_LIMIT_COUNT, RATE_LIMIT_WINDOW_SECONDS

_requests = defaultdict(deque)

def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def check_csrf(request: Request, submitted: str) -> None:
    cookie = request.cookies.get("parcel_csrf", "")
    if not cookie or not submitted or not secrets.compare_digest(cookie, submitted):
        raise HTTPException(403, "Request validation failed")

def check_request_size(request: Request) -> None:
    value = request.headers.get("content-length")
    if value:
        try:
            if int(value) > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Request too large")
        except ValueError as exc:
            raise HTTPException(400, "Invalid request") from exc

def check_rate(request: Request) -> None:
    now = time.monotonic()
    client = request.client.host if request.client else "local"
    bucket = _requests[client]
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_COUNT:
        raise HTTPException(429, "Too many requests")
    bucket.append(now)
