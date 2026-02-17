FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN python -m pip install --no-cache-dir uv

# Copy project metadata first for better layer caching
COPY services/s1-ingest-nocodb/pyproject.toml /app/pyproject.toml

# Copy source code
COPY services/s1-ingest-nocodb/src /app/src

# Copy shared package source
COPY packages/core /app/packages/core

# Install runtime dependencies
RUN uv sync --no-dev
RUN uv pip install --python /app/.venv/bin/python /app/packages/core

EXPOSE 7101

CMD ["uv", "run", "uvicorn", "ingest_nocodb.app:app", "--host", "0.0.0.0", "--port", "7101"]
