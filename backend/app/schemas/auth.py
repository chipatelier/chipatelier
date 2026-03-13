"""Pydantic v2 schemas for authentication and user responses."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response body carrying a JWT access token."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user profile returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None
    role: str
    storage_used_bytes: int
    created_at: datetime
