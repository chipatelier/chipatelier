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
        self._internal_endpoint = f"http://{settings.MINIO_ENDPOINT}"
        self._client = boto3.client(
            "s3",
            endpoint_url=self._internal_endpoint,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            # REQUIRED for MinIO — without s3v4 presigned URLs return 403
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self._bucket = settings.S3_BUCKET_ARTIFACTS
        # Public URL used to rewrite presigned URLs before returning them to the browser.
        # MinIO's internal hostname (e.g. "minio:9000") is not resolvable outside Docker.
        public = settings.MINIO_PUBLIC_URL or settings.MINIO_ENDPOINT
        self._public_endpoint = f"http://{public}"

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
        """Generate a presigned GET URL for the given key.

        The boto3 client signs against the internal endpoint URL. If MINIO_PUBLIC_URL
        differs, we rewrite the hostname so the URL is resolvable from the browser.
        """
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expiry,
        )
        if self._public_endpoint != self._internal_endpoint:
            url = url.replace(self._internal_endpoint, self._public_endpoint, 1)
        return url

    def download_file_to_path(self, key: str, local_path: str) -> None:
        """Download a file from S3/MinIO to a local path."""
        self._client.download_file(self._bucket, key, local_path)

    def download_file(self, key: str) -> bytes:
        """Download an object from S3/MinIO and return its bytes."""
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def list_files(self, prefix: str) -> list[str]:
        """List all object keys under the given S3/MinIO prefix."""
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

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
