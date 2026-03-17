"""Security utilities: password hashing and JWT token management."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash a plaintext password using argon2id."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an argon2id hash. Returns False on mismatch."""
    try:
        _ph.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    """Create a short-lived JWT access token (15 min default)."""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived JWT refresh token with jti for denylist support (7 days default)."""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": str(uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_vnc_token(user_id: str, run_id: str, port: int) -> str:
    """Create a scoped VNC session token (2hr expiry, separate secret)."""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "run_id": run_id,
        "port": port,
        "type": "vnc",
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    return jwt.encode(payload, settings.VNC_TOKEN_SECRET, algorithm="HS256")


def decode_token(token: str, secret: str | None = None) -> dict:
    """Decode and validate a JWT token.

    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        secret or settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
