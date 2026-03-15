"""Pydantic schemas for assignment endpoints."""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssignmentCreate(BaseModel):
    """Request body for POST /api/v1/courses/{course_id}/assignments."""

    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = None
    pdk: str = "sky130hd"
    target_stage: str = "route"
    locked_params: dict[str, Any] = Field(default_factory=dict)
    editable_params: list[str] = Field(default_factory=list)
    checkpoint_rules: dict[str, Any] = Field(default_factory=dict)
    due_at: Optional[datetime] = None
    orfs_version: Optional[str] = None

    @field_validator("locked_params", mode="before")
    @classmethod
    def coerce_locked_params_values_to_str(cls, v: Any) -> dict[str, str]:
        """Ensure all locked_params values are stored as strings.

        ORFS locked params are passed via Make command line as strings.
        Storing as str prevents int/str mismatch bugs in JSONB.
        """
        if not isinstance(v, dict):
            return v
        return {k: str(val) for k, val in v.items()}


class AssignmentResponse(BaseModel):
    """Response schema for assignment endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: Optional[str]
    pdk: str
    target_stage: str
    locked_params: dict[str, Any]
    editable_params: list[str]
    checkpoint_rules: dict[str, Any]
    due_at: Optional[datetime]
    is_open: bool
    orfs_version: Optional[str]
    created_at: datetime

    @field_validator("locked_params", mode="before")
    @classmethod
    def coerce_locked_params_values_to_str(cls, v: Any) -> dict[str, str]:
        """Coerce locked_params values to str on both create and response."""
        if not isinstance(v, dict):
            return v
        return {k: str(val) for k, val in v.items()}


class AssignmentOpenToggle(BaseModel):
    """Request body for PATCH /api/v1/assignments/{id}/open."""

    is_open: bool
