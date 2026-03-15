"""Pydantic schemas for click-to-inspect layout query endpoint."""
from pydantic import BaseModel


class InspectElement(BaseModel):
    """A single layout instance returned by a spatial query."""

    name: str
    master: str | None
    nets: list[str]


class InspectResponse(BaseModel):
    """Response schema for GET /api/v1/query/{run_id}."""

    elements: list[InspectElement]
    run_id: str
    x_um: float
    y_um: float
