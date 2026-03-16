"""Application settings sourced from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://chipatelier:changeme@postgres:5432/chipatelier"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Storage
    STORAGE_BACKEND: str = "minio"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_ARTIFACTS: str = "chipatelier-artifacts"

    # Auth
    JWT_SECRET_KEY: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    VNC_TOKEN_SECRET: str = "change_me_in_production"

    # OpenROAD
    # Note: PDK_ROOT is NOT used by ORFS. ORFS bundles all platform files (sky130hd,
    # gf180, asap7) inside the image at /OpenROAD-flow-scripts/flow/platforms/.
    # PDK_ROOT is an OpenLane variable — do not add it here.
    ORFS_IMAGE: str = "openroad/orfs:latest"
    ARTIFACTS_ROOT: str = "/data/artifacts"
    WARM_POOL_SIZE: int = 4
    MAX_CONCURRENT_JOBS: int = 12
    JOB_TIMEOUT_SECONDS: int = 7200
    JOB_CPU_CORES: int = 6
    JOB_RAM_GB: int = 8
    JOB_DISK_GB: int = 5

    # VNC
    MAX_VNC_SESSIONS: int = 8

    # Worker configuration
    ORFS_WORKER_CONCURRENCY: int = 4
    BACKGROUND_WORKER_CONCURRENCY: int = 2

    # AI Service
    LLM_BACKEND: str = "ollama"
    OLLAMA_BASE_URL: str = "http://ai-service:11434"
    ANTHROPIC_API_KEY: str = ""

    # Domain
    ALLOWED_ORIGINS: str = "*"

    # Security - Cookie settings
    COOKIE_SECURE: bool = False  # Set to True in production with HTTPS

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
