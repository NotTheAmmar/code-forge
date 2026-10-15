"""Authentication service: password hashing and JWT token management."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored *hashed* password."""
    return _pwd_context.verify(plain, hashed)


# ── JWT token creation ────────────────────────────────────────────────────────

def _create_token(
    payload: dict[str, Any],
    expires_delta: timedelta,
) -> str:
    """Sign and return a JWT with the given payload and expiry."""
    now = datetime.now(tz=timezone.utc)
    data = payload.copy()
    data.update({"iat": now, "exp": now + expires_delta})
    return jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, role: str) -> str:
    """Create a short-lived access token for the given user."""
    return _create_token(
        {"sub": user_id, "role": role, "type": "access"},
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token for the given user."""
    return _create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


# ── JWT token verification ────────────────────────────────────────────────────

class TokenError(Exception):
    """Raised when a JWT cannot be validated."""


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token.

    Returns the decoded payload dict.
    Raises TokenError on any validation failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired")
    except jwt.InvalidTokenError as exc:
        raise TokenError(str(exc))

    if payload.get("type") != "access":
        raise TokenError("Invalid token type")

    return payload


def decode_refresh_token(token: str) -> str:
    """Decode a refresh token and return the user_id (sub claim).

    Raises TokenError on any validation failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise TokenError("Refresh token has expired")
    except jwt.InvalidTokenError as exc:
        raise TokenError(str(exc))

    if payload.get("type") != "refresh":
        raise TokenError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise TokenError("Missing subject in token")

    return sub
