"""Pydantic schemas for submission endpoints."""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class SubmitRequest(BaseModel):
    """Request body for POST /api/v1/assignments/{id}/submit."""
    run_id: uuid.UUID


class SubmissionResponse(BaseModel):
    """Response schema for submission endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assignment_id: uuid.UUID
    run_id: uuid.UUID
    user_id: uuid.UUID
    score: Optional[float] = None
    grading_status: str
    checkpoint_results: Optional[dict[str, Any]] = None
    submitted_at: datetime


class PreviewScoreResponse(BaseModel):
    """Response for GET /assignments/{id}/preview-score (no submission created)."""
    checkpoint_results: dict[str, Any]
    score: float
    is_eligible: bool  # True if no locked param violations
