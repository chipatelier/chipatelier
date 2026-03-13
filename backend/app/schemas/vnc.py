"""Pydantic schemas for VNC session endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VncStartResponse(BaseModel):
    """Response from POST /vnc/start/{run_id}."""

    session_id: uuid.UUID
    token: str
    vnc_url: str  # "/vnc/{token}" — opened in new browser tab
    expires_at: datetime


class VncSessionResponse(BaseModel):
    """Full VNC session details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    status: str
    port: int | None
    created_at: datetime
    expires_at: datetime | None
