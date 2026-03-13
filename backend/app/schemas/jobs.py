"""Pydantic schemas for job submission and status endpoints."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SubmitRequest(BaseModel):
    project_id: uuid.UUID
    target_stage: str = "gds"  # synthesis | floorplan | place | cts | route | gds
    config_overrides: dict[str, Any] = {}
    source_path: str | None = None  # Path to uploaded files in MinIO (e.g., "projects/{id}/v1")


class SubmitResponse(BaseModel):
    run_id: uuid.UUID
    status: str = "queued"


class RunStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    stage_completed: str | None
    target_stage: str | None
    created_at: datetime
    completed_at: datetime | None
    ppa: dict[str, Any] | None
