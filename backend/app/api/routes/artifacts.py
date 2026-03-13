"""Artifact download endpoint.

Routes:
    GET /jobs/{run_id}/artifacts — return presigned download URLs for all artifacts.
"""
import uuid

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.schemas.artifacts import ArtifactURLs
from app.services.storage_service import StorageService, get_storage_service

router = APIRouter(prefix="/jobs", tags=["artifacts"])

_ARTIFACT_EXPIRY = 3600  # 1 hour


def _try_presign(storage: StorageService, key: str, expiry: int = _ARTIFACT_EXPIRY) -> str | None:
    """Return a presigned URL for the given key, or None if the object does not exist."""
    try:
        return storage.generate_download_url(key, expiry=expiry)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            return None
        # Re-raise unexpected errors
        raise


@router.get("/{run_id}/artifacts", response_model=ArtifactURLs)
async def get_artifacts(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
) -> ArtifactURLs:
    """Return presigned download URLs for a completed run's artifacts.

    Requires the run to have an artifact_path set (job must be complete).
    Returns 404 if artifacts are not yet available.
    Each URL expires after 1 hour.
    """
    run: Run | None = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    # Verify ownership via project
    project: Project | None = await db.get(Project, run.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if not run.artifact_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job artifacts not yet available. Job may still be running or failed.",
        )

    prefix = run.artifact_path  # e.g., "runs/{run_id}/"

    # Generate presigned URLs for each artifact type that exists in MinIO
    gds_url = _try_presign(storage, f"{prefix}6_final.gds")
    def_url = _try_presign(storage, f"{prefix}6_final.def")
    timing_url = _try_presign(storage, f"{prefix}reports/timing.rpt")
    png_url = _try_presign(storage, f"{prefix}layout.png")

    return ArtifactURLs(
        run_id=str(run_id),
        gds_url=gds_url,
        def_url=def_url,
        timing_report_url=timing_url,
        layout_png_url=png_url,
        expires_in_seconds=_ARTIFACT_EXPIRY,
    )
