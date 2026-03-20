"""Background task stubs for storage cleanup. Actual execution happens in Celery worker."""


def purge_project_artifacts(project_id: str, artifact_paths: list[str]) -> None:
    """Purge all MinIO objects for a deleted project.

    Called as purge_project_artifacts.delay(...) from the delete endpoint.
    Actual execution happens in Celery worker process.
    """
    from app.services.storage_service import StorageService
    from app.core.config import get_settings

    storage = StorageService(get_settings())
    storage.delete_prefix(f"projects/{project_id}/")
    for path in artifact_paths:
        if path:
            storage.delete_prefix(path)
