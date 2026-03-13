"""FastAPI dependencies: authentication and authorization helpers."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Bearer token and return the authenticated user.

    Raises 401 if token is missing, expired, malformed, or if user is inactive.
    """
    try:
        payload = decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise _credentials_exception

    if payload.get("type") != "access":
        raise _credentials_exception

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise _credentials_exception

    try:
        from uuid import UUID

        uid = UUID(user_id)
    except (ValueError, AttributeError):
        raise _credentials_exception

    user = await db.get(User, uid)
    if not user or not user.is_active:
        raise _credentials_exception

    return user


def require_role(*roles: str):
    """Dependency factory: require the authenticated user to have one of the given roles."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _check
