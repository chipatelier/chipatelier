"""Project management endpoints.

Routes:
    POST   /projects           — create project
    GET    /projects           — list current user's projects
    GET    /projects/{id}      — get project details
    POST   /projects/{id}/upload  — upload Verilog/config files to MinIO
    GET    /projects/{id}/runs — list runs for project
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.schemas.projects import ProjectCreate, ProjectResponse, RunSummary, UploadResponse
from app.services.storage_service import StorageService, get_storage_service

router = APIRouter(prefix="/projects", tags=["projects"])

# Allowed file extensions for design uploads
_ALLOWED_EXTENSIONS = {".v", ".sv", ".mk"}


def _check_ownership(project: Project, user: User) -> None:
    """Raise 403 if the project does not belong to the user."""
    if project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def _get_project_or_404(project_id: uuid.UUID, db: AsyncSession) -> Project:
    """Fetch a project by ID or raise 404."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


# ---------------------------------------------------------------------------
# POST /projects — Create project
# ---------------------------------------------------------------------------

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Create a new project for the authenticated user."""
    project = Project(
        user_id=user.id,
        name=body.name,
        pdk=body.pdk,
        storage_bytes=0,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        pdk=project.pdk,
        storage_bytes=project.storage_bytes,
        created_at=project.created_at,
        run_count=0,
    )


# ---------------------------------------------------------------------------
# GET /projects — List user's projects
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    """Return all projects owned by the current user."""
    result = await db.execute(
        select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    responses = []
    for project in projects:
        # Count runs for this project
        count_result = await db.execute(
            select(func.count()).where(Run.project_id == project.id)
        )
        run_count = count_result.scalar_one() or 0
        responses.append(ProjectResponse(
            id=project.id,
            name=project.name,
            pdk=project.pdk,
            storage_bytes=project.storage_bytes,
            created_at=project.created_at,
            run_count=run_count,
        ))
    return responses


# ---------------------------------------------------------------------------
# GET /projects/{id} — Get single project
# ---------------------------------------------------------------------------

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Get project details. Only the owner can access their project."""
    project = await _get_project_or_404(project_id, db)
    _check_ownership(project, user)

    count_result = await db.execute(
        select(func.count()).where(Run.project_id == project.id)
    )
    run_count = count_result.scalar_one() or 0
    return ProjectResponse(
        id=project.id,
        name=project.name,
        pdk=project.pdk,
        storage_bytes=project.storage_bytes,
        created_at=project.created_at,
        run_count=run_count,
    )


# ---------------------------------------------------------------------------
# POST /projects/{id}/upload — Upload design files
# ---------------------------------------------------------------------------

@router.post("/{project_id}/upload", response_model=UploadResponse)
async def upload_files(
    project_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    top_module: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
) -> UploadResponse:
    """Upload Verilog (.v, .sv) and config (.mk) files to MinIO.

    Files are stored at: projects/{project_id}/v{N}/{filename}
    where N is the next version number.
    """
    project = await _get_project_or_404(project_id, db)
    _check_ownership(project, user)

    # Validate file extensions
    for file in files:
        filename = file.filename or ""
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{filename}' has unsupported extension. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}",
            )

    # Determine version number: count existing runs to derive version
    # (In Phase 1 we don't have a source_versions table, so we use artifact_path convention)
    from sqlalchemy import select as sa_select
    runs_result = await db.execute(
        sa_select(func.count()).where(Run.project_id == project_id)
    )
    version_num = (runs_result.scalar_one() or 0) + 1

    source_path = f"projects/{project_id}/v{version_num}"
    total_bytes = 0

    # Upload each file
    for file in files:
        content = await file.read()
        key = f"{source_path}/{file.filename}"
        storage.upload_file(key, content, file.content_type or "application/octet-stream")
        total_bytes += len(content)

    # Update project storage_bytes
    project.storage_bytes += total_bytes
    await db.commit()

    return UploadResponse(source_path=source_path, file_count=len(files))


# ---------------------------------------------------------------------------
# GET /projects/{id}/runs — List runs for project
# ---------------------------------------------------------------------------

@router.get("/{project_id}/runs", response_model=list[RunSummary])
async def list_runs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RunSummary]:
    """Return all runs for a project, ordered newest first."""
    project = await _get_project_or_404(project_id, db)
    _check_ownership(project, user)

    result = await db.execute(
        select(Run)
        .where(Run.project_id == project_id)
        .order_by(Run.created_at.desc())
    )
    runs = result.scalars().all()
    return [RunSummary.model_validate(run) for run in runs]
