import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import receiver_token


def post_internal(url, note, record_id, timeout=10):
    body = json.dumps({"record_id": record_id, "note": note}).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {receiver_token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False
