"""Project management endpoints.

Routes:
    POST   /projects              — create project
    GET    /projects              — list current user's projects
    GET    /projects/{id}         — get project details
    DELETE /projects/{id}         — delete project and queue artifact purge
    PATCH  /projects/{id}         — rename and/or save config.mk
    POST   /projects/{id}/upload  — upload Verilog/config files to MinIO
    GET    /projects/{id}/runs    — list runs for project
    GET    /projects/{id}/source  — fetch latest Verilog content
    GET    /projects/{id}/config  — fetch current config.mk content
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
from app.schemas.projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    RunSummary,
    UploadResponse,
)
from app.services.storage_service import StorageService, get_storage_service

router = APIRouter(prefix="/projects", tags=["projects"])

# Allowed file extensions for design uploads
_ALLOWED_EXTENSIONS = {".v", ".sv", ".mk", ".sdc"}


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


def _build_project_response(project: Project, run_count: int) -> ProjectResponse:
    """Build a ProjectResponse from a Project model and run count."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        pdk=project.pdk,
        storage_bytes=project.storage_bytes,
        created_at=project.created_at,
        run_count=run_count,
        config_version=project.config_version,
        verilog_version=project.verilog_version,
        latest_source_path=project.latest_source_path,
    )


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

    return _build_project_response(project, 0)


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
        responses.append(_build_project_response(project, run_count))
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
    return _build_project_response(project, run_count)


# ---------------------------------------------------------------------------
# DELETE /projects/{id} — Delete project and queue artifact purge
# ---------------------------------------------------------------------------

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete a project. Blocks if an active run exists."""
    project = await _get_project_or_404(project_id, db)
    _check_ownership(project, user)

    # Block delete if active run exists
    active_result = await db.execute(
        select(Run).where(
            Run.project_id == project_id,
            Run.status.in_(["queued", "starting", "running"]),
        )
    )
    if active_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancel the active run before deleting this project",
        )

    # Collect run artifact paths before deletion
    runs_result = await db.execute(select(Run).where(Run.project_id == project_id))
    artifact_paths = [r.artifact_path for r in runs_result.scalars().all() if r.artifact_path]

    # Delete project (cascades to runs via ORM relationship)
    await db.delete(project)
    await db.commit()

    # Queue MinIO purge as background Celery task (best-effort)
    import logging
    _logger = logging.getLogger(__name__)
    try:
        from app.core.celery_client import celery_app as _celery
        _celery.send_task(
            "tasks.storage_cleanup.purge_project_artifacts",
            args=[str(project_id), artifact_paths],
        )
    except ImportError:
        _logger.warning(
            "Celery not available in this context; project artifact purge skipped for project %s",
            project_id,
        )
    except Exception as exc:
        _logger.warning("Failed to queue artifact purge for project %s: %s", project_id, exc)


# ---------------------------------------------------------------------------
# PATCH /projects/{id} — Rename and/or save config.mk
# ---------------------------------------------------------------------------

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
) -> ProjectResponse:
    """Update project name and/or config.mk content."""
    project = await _get_project_or_404(project_id, db)
    _check_ownership(project, user)

    if body.name is not None:
        # Check duplicate name for this user
        dup = await db.execute(
            select(Project).where(
                Project.user_id == user.id,
                Project.name == body.name,
                Project.id != project_id,
            )
        )
        if dup.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A project with that name already exists",
            )
        project.name = body.name

    if body.config_mk is not None:
        new_version = project.config_version + 1
        key = f"projects/{project_id}/config/v{new_version}/config.mk"
        # Write to MinIO FIRST — only increment DB version on success
        storage.upload_file(key, body.config_mk.encode(), "text/plain")
        project.config_version = new_version

    await db.commit()
    await db.refresh(project)

    count_result = await db.execute(select(func.count()).where(Run.project_id == project.id))
    run_count = count_result.scalar_one() or 0
    return _build_project_response(project, run_count)


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
    """Upload Verilog (.v, .sv) and config (.mk, .sdc) files to MinIO.

    Files are stored at: projects/{project_id}/verilog/v{N}/{filename}
    where N is the next verilog_version number.
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

    # Use verilog_version for upload versioning
    new_version = project.verilog_version + 1
    source_path = f"projects/{project_id}/verilog/v{new_version}"
    total_bytes = 0

    # Upload each file
    for file in files:
        content = await file.read()
        key = f"{source_path}/{file.filename}"
        storage.upload_file(key, content, file.content_type or "application/octet-stream")
        total_bytes += len(content)

    # Update project tracking fields
    project.storage_bytes += total_bytes
    project.verilog_version = new_version
    project.latest_source_path = source_path
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


# ---------------------------------------------------------------------------
# GET /projects/{id}/source — Fetch latest Verilog content for display
# ---------------------------------------------------------------------------

@router.get("/{project_id}/source")
async def get_project_source(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
) -> dict:
    """Return the latest uploaded Verilog source content."""
    project = await _get_project_or_404(project_id, db)
    _check_ownership(project, user)

    if project.latest_source_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Verilog uploaded yet")

    prefix = project.latest_source_path + "/"
    files = storage.list_files(prefix)
    verilog_files = sorted([f for f in files if f.endswith((".v", ".sv"))])

    if not verilog_files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Verilog uploaded yet")

    parts = [storage.download_file(f).decode("utf-8", errors="replace") for f in verilog_files]
    content = "\n\n".join(parts)

    if len(verilog_files) == 1:
        filename = verilog_files[0].split("/")[-1]
    else:
        first = verilog_files[0].split("/")[-1]
        filename = f"{first} ({len(verilog_files)} files)"

    return {"filename": filename, "content": content, "version": project.verilog_version}


# ---------------------------------------------------------------------------
# GET /projects/{id}/config — Fetch current config.mk content
# ---------------------------------------------------------------------------

@router.get("/{project_id}/config")
async def get_project_config(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
) -> dict:
    """Return the current config.mk content and version."""
    project = await _get_project_or_404(project_id, db)
    _check_ownership(project, user)

    if project.config_version == 0:
        return {"content": "", "version": 0}

    key = f"projects/{project_id}/config/v{project.config_version}/config.mk"
    try:
        content = storage.download_file(key).decode("utf-8", errors="replace")
    except Exception:
        content = ""
    return {"content": content, "version": project.config_version}
