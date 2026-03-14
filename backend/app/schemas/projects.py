"""Pydantic schemas for project and run endpoints."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    pdk: str = "sky130hd"


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    pdk: str
    storage_bytes: int
    created_at: datetime
    run_count: int = 0


class RunSummary(BaseModel):
    """Run summary for list endpoints.

    notes intentionally excluded — private, only in RunStatusResponse (GET /jobs/{id}).
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    target_stage: str | None
    stage_completed: str | None
    queue_priority: str
    created_at: datetime
    completed_at: datetime | None
    ppa: dict[str, Any] | None
    # notes intentionally excluded — private


class UploadResponse(BaseModel):
    source_path: str
    file_count: int
