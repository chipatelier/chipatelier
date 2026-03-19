"""Pydantic schemas for admin endpoints."""
from pydantic import BaseModel, EmailStr


class GenerateResetTokenRequest(BaseModel):
    """Request body to generate a password reset token for a user."""

    email: EmailStr


class ResetTokenResponse(BaseModel):
    """Response carrying the generated reset token."""

    token: str
    expires_in_seconds: int
