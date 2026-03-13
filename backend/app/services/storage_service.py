"""MinIO/S3 storage abstraction.

Uses boto3 with S3v4 signature required for MinIO compatibility.
CRITICAL: signature_version='s3v4' is required — boto3 with MinIO fails with 403
presigned URLs without it (minio/minio#8132).
"""
from typing import Any

import boto3
from botocore.config import Config


class StorageService:
    """Wraps MinIO/S3 with upload, presigned download URL, and prefix deletion."""

    def __init__(self, settings: Any) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            # REQUIRED for MinIO — without s3v4 presigned URLs return 403
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self._bucket = settings.S3_BUCKET_ARTIFACTS

    def upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to the given S3 key. Returns the key."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def generate_download_url(self, key: str, expiry: int = 3600) -> str:
        """Generate a presigned GET URL for the given key."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expiry,
        )

    def delete_prefix(self, prefix: str) -> int:
        """Delete all objects with the given prefix. Returns count of deleted objects."""
        count = 0
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            objects = page.get("Contents", [])
            if not objects:
                continue
            delete_payload = {"Objects": [{"Key": obj["Key"]} for obj in objects]}
            self._client.delete_objects(Bucket=self._bucket, Delete=delete_payload)
            count += len(objects)
        return count


def get_storage_service() -> StorageService:
    """FastAPI dependency that returns a StorageService instance."""
    from app.core.config import get_settings
    return StorageService(get_settings())
