"""Pydantic schemas for course and enrollment endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    """Request body for POST /api/v1/courses."""

    name: str = Field(min_length=1, max_length=200)
    term: Optional[str] = None


class CourseResponse(BaseModel):
    """Response schema for course endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    term: Optional[str]
    is_active: bool
    enrollment_code: str
    created_at: datetime


class EnrollRequest(BaseModel):
    """Request body for POST /api/v1/courses/{course_id}/enroll."""

    enrollment_code: str = Field(min_length=1)


class EnrollResponse(BaseModel):
    """Response schema after successful enrollment."""

    model_config = ConfigDict(from_attributes=True)

    course_id: uuid.UUID
    course_name: str
    enrolled_at: datetime
