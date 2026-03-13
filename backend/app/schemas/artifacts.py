"""Pydantic schemas for artifact download endpoints."""
from pydantic import BaseModel


class ArtifactURLs(BaseModel):
    """Presigned download URLs for a completed run's artifacts.

    All URLs expire after expires_in_seconds (default 1 hour).
    Fields are None if the artifact does not exist in storage.
    """

    gds_url: str | None = None
    def_url: str | None = None
    timing_report_url: str | None = None
    layout_png_url: str | None = None
    run_id: str
    expires_in_seconds: int = 3600
