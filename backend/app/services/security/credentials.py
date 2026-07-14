"""Versioned one-way credential encodings.

Presented session and API-token values use ``record-id.secret``. The record ID
allows one bounded lookup; only a salted digest of the random secret is stored.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


SCRYPT_N = 32768
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
DERIVED_KEY_BYTES = 32
SECRET_BYTES = 32
SCRYPT_MAX_MEMORY = 64 * 1024 * 1024


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a self-describing scrypt/v1 password verifier."""

    if not 12 <= len(password) <= 1024:
        raise ValueError("Password length must be between 12 and 1024 characters")
    actual_salt = salt or secrets.token_bytes(SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=actual_salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=DERIVED_KEY_BYTES,
        maxmem=SCRYPT_MAX_MEMORY,
    )
    return "$".join(
        (
            "scrypt",
            "v1",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _encode(actual_salt),
            _encode(digest),
        )
    )


def verify_password(password: str, verifier: str) -> bool:
    try:
        algorithm, version, n, r, p, salt, expected = verifier.split("$")
        if (algorithm, version, int(n), int(r), int(p)) != (
            "scrypt",
            "v1",
            SCRYPT_N,
            SCRYPT_R,
            SCRYPT_P,
        ):
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode(salt),
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=DERIVED_KEY_BYTES,
            maxmem=SCRYPT_MAX_MEMORY,
        )
        return hmac.compare_digest(actual, _decode(expected))
    except (TypeError, ValueError):
        return False


def issue_secret(record_id: str) -> tuple[str, str]:
    """Return the one-time presented value and its salted stored verifier."""

    secret = secrets.token_urlsafe(SECRET_BYTES)
    return f"{record_id}.{secret}", hash_secret(secret)


def hash_secret(secret: str, *, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(SALT_BYTES)
    digest = hashlib.sha256(actual_salt + secret.encode("utf-8")).digest()
    return "$".join(("sha256", "v1", _encode(actual_salt), _encode(digest)))


def verify_presented_secret(presented: str, record_id: str, verifier: str) -> bool:
    prefix, separator, secret = presented.partition(".")
    if separator != "." or prefix != record_id or not secret:
        return False
    try:
        algorithm, version, salt, expected = verifier.split("$")
        if (algorithm, version) != ("sha256", "v1"):
            return False
        actual = hashlib.sha256(_decode(salt) + secret.encode("utf-8")).digest()
        return hmac.compare_digest(actual, _decode(expected))
    except (TypeError, ValueError):
        return False


def credential_record_id(presented: str, expected_prefix: str) -> str | None:
    record_id, separator, secret = presented.partition(".")
    if separator != "." or not record_id.startswith(expected_prefix) or not secret:
        return None
    return record_id


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
