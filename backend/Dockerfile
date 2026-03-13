FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency manifest + source together so hatchling can find the package
COPY pyproject.toml ./
COPY app ./app

# Install production dependencies (non-editable; editable mode is meaningless in Docker)
RUN uv pip install --system --no-cache .

# Copy remaining files (alembic, tests, etc.)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
