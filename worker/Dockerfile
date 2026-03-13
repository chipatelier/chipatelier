FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Install Celery + dependencies
RUN uv pip install --system --no-cache \
    "celery[redis]==5.4.*" \
    "redis==5.*" \
    "docker==7.1.*" \
    "boto3==1.35.*" \
    "pydantic-settings==2.*" \
    "sqlalchemy[asyncio]==2.0.*" \
    "asyncpg==0.29.*"

# Copy worker source
COPY . .

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
