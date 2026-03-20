"""Pydantic schemas for job submission and status endpoints."""
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class TargetStage(StrEnum):
    """Valid ORFS Make targets for job submission."""
    SYNTH = "synth"
    FLOORPLAN = "floorplan"
    PLACE = "place"
    CTS = "cts"
    ROUTE = "route"
    FINISH = "finish"


class SubmitRequest(BaseModel):
    project_id: uuid.UUID
    target_stage: TargetStage = TargetStage.FINISH
    config_overrides: dict[str, str] = {}   # str values — Make args are always strings
    source_path: str | None = None  # Path to uploaded files in MinIO (e.g., "projects/{id}/v1")
    notes: str | None = None


class SubmitResponse(BaseModel):
    run_id: uuid.UUID
    status: str = "queued"
    queue_priority: str = "normal"


class RunSummary(BaseModel):
    """Run summary for list endpoints — notes intentionally excluded (private)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    target_stage: str | None
    stage_completed: str | None
    queue_priority: str
    created_at: datetime
    completed_at: datetime | None
    ppa: dict[str, Any] | None
    # notes intentionally excluded — private, only in RunStatusResponse


class RunStatusResponse(BaseModel):
    """Full run detail — includes notes (visible to run owner only)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    stage_completed: str | None
    target_stage: str | None
    queue_priority: str
    notes: str | None   # included here — owner can see their own run notes
    created_at: datetime
    completed_at: datetime | None
    ppa: dict[str, Any] | None


class RunNotesUpdate(BaseModel):
    """Request body for PATCH /runs/{id}/notes."""
    notes: str | None = None   # None clears the notes
    model_config = ConfigDict(str_max_length=2000)
