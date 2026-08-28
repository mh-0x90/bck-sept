import json

MAX_MESSAGE_BYTES = 64 * 1024


def encode_message(value: dict) -> bytes:
    return (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")


def decode_message(raw: bytes) -> dict:
    if not raw:
        raise ValueError("empty message")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("message too large")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("message must be an object")
    return value
