import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAGIC = b"PRTMP1"
_NONCE_BYTES = 12
_KEY_BYTES = 32
_AAD = _MAGIC


class TempFileCryptoError(ValueError):
    """Raised when an encrypted temporary file cannot be safely decrypted."""


def _key() -> bytes:
    encoded = os.getenv("PARCEL_TMP_ENCRYPTION_KEY", "").strip()
    if not encoded:
        raise RuntimeError(
            "PARCEL_TMP_ENCRYPTION_KEY is required; set it to a URL-safe base64 "
            "encoded 32-byte key"
        )
    try:
        key = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("PARCEL_TMP_ENCRYPTION_KEY is not valid URL-safe base64") from exc
    if len(key) != _KEY_BYTES:
        raise RuntimeError("PARCEL_TMP_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def encrypt_text(plaintext: str) -> bytes:

    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(_key()).encrypt(nonce, plaintext.encode("utf-8"), _AAD)
    return _MAGIC + nonce + ciphertext


def decrypt_text(payload: bytes) -> str:
    minimum_size = len(_MAGIC) + _NONCE_BYTES + 16
    if len(payload) < minimum_size or not payload.startswith(_MAGIC):
        raise TempFileCryptoError("Temporary file has an invalid encrypted format")

    nonce_start = len(_MAGIC)
    nonce_end = nonce_start + _NONCE_BYTES
    nonce = payload[nonce_start:nonce_end]
    ciphertext = payload[nonce_end:]
    try:
        plaintext = AESGCM(_key()).decrypt(nonce, ciphertext, _AAD)
    except InvalidTag as exc:
        raise TempFileCryptoError("Temporary file authentication failed") from exc

    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TempFileCryptoError("Temporary file plaintext is not valid UTF-8") from exc
