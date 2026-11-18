import mimetypes
from pathlib import Path
from urllib.parse import unquote

from config import INTERNAL_FILE_LIMIT

PRIVATE_DIR = (Path(__file__).resolve().parent / "private").resolve()


def read_private_file(request_path):
    relative = unquote(request_path.removeprefix("/files/")).lstrip("/")
    if not relative:
        return 404, b"", "application/octet-stream"

    candidate = (PRIVATE_DIR / relative).resolve()
    try:
        candidate.relative_to(PRIVATE_DIR)
    except ValueError:
        return 404, b"", "application/octet-stream"

    if not candidate.is_file():
        return 404, b"", "application/octet-stream"

    try:
        with candidate.open("rb") as handle:
            body = handle.read(INTERNAL_FILE_LIMIT + 1)
    except OSError:
        return 404, b"", "application/octet-stream"

    if len(body) > INTERNAL_FILE_LIMIT:
        return 413, b"", "application/octet-stream"

    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    return 200, body, content_type
