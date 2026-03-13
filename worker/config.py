"""Worker configuration - mirrors backend settings needed by worker tasks."""
import os
from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """Settings for worker tasks."""
    DATABASE_URL: str = "postgresql://chipatelier:changeme@postgres:5432/chipatelier"
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Storage
    STORAGE_BACKEND: str = "minio"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_ARTIFACTS: str = "chipatelier-artifacts"
    
    # OpenROAD
    ORFS_IMAGE: str = "openroad/orfs:latest"
    PDK_ROOT: str = "/data/pdks"
    ARTIFACTS_ROOT: str = "/data/artifacts"
    JOB_TIMEOUT_SECONDS: int = 7200
    JOB_CPU_CORES: int = 6
    JOB_RAM_GB: int = 8
    JOB_DISK_GB: int = 5
    
    class Config:
        env_file = ".env"
        extra = "ignore"


def get_settings() -> WorkerSettings:
    """Return settings instance."""
    return WorkerSettings()
