"""Security helpers for account and session handling."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from typing import Optional


PASSWORD_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260_000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-\u4e00-\u9fa5]{3,32}$")


class SecurityError(ValueError):
    """Raised when user-controlled security input is invalid."""


def validate_username(username: str) -> str:
    username = (username or "").strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise SecurityError("Username must be 3-32 chars: letters, numbers, _, -, or Chinese chars.")
    return username


def validate_password(password: str) -> str:
    if not isinstance(password, str):
        raise SecurityError("Password is required.")
    if len(password) < 6:
        raise SecurityError("Password must contain at least 6 characters.")
    if len(password) > 128:
        raise SecurityError("Password must be no longer than 128 characters.")
    return password


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    validate_password(password)
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{PASSWORD_SCHEME}${PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not password or not stored_hash:
        return False
    try:
        scheme, iterations, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        salt = _b64decode(salt_b64)
        expected = _b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
