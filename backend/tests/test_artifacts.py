"""Wave 0 stub: artifact storage tests — implemented in plan 01-04."""
import pytest


async def test_upload_artifact(mock_s3):
    """Artifacts can be uploaded to MinIO/S3."""
    pass


async def test_download_artifact(mock_s3):
    """Artifacts can be downloaded from MinIO/S3."""
    pass


async def test_artifact_presigned_url(mock_s3):
    """Presigned URLs are generated for artifact downloads."""
    pass


async def test_artifact_storage_quota(async_session, mock_s3):
    """Storage quota is enforced when uploading artifacts."""
    pass
