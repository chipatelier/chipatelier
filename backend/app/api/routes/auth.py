"""Authentication endpoints: register, login, logout, refresh."""
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    """Register a new user account.

    Returns 409 if the email is already registered.
    """
    # Check for duplicate email first (avoids catching unrelated IntegrityErrors)
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        role="student",
        is_active=True,
        storage_used_bytes=0,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return access token + httpOnly refresh cookie."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account disabled",
        )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    # Set refresh token as httpOnly cookie scoped to auth endpoints.
    # Path=/api/v1/auth/ so it is sent to both /logout and /refresh
    # but NOT to general API routes, limiting exposure.
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    redis=Depends(get_redis),
) -> None:
    """Logout: add refresh token jti to Redis denylist and clear cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    try:
        payload = decode_token(refresh_token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        # Token invalid — still clear cookie, don't expose reason
        response.delete_cookie("refresh_token", path="/api/v1/auth")
        return

    jti: str | None = payload.get("jti")
    if jti:
        # Calculate remaining TTL and add to denylist
        exp = payload.get("exp", 0)
        remaining_ttl = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
        await redis.set(f"denylist:{jti}", "1", ex=remaining_ttl)

    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str | None = Cookie(default=None),
    redis=Depends(get_redis),
) -> TokenResponse:
    """Exchange a valid refresh cookie for a new access token."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    try:
        payload = decode_token(refresh_token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Check denylist
    jti: str | None = payload.get("jti")
    if jti:
        denied = await redis.get(f"denylist:{jti}")
        if denied:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    access_token = create_access_token(user_id)
    return TokenResponse(access_token=access_token)
