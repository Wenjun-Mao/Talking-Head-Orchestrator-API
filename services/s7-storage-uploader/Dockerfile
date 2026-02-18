FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir uv

COPY services/s7-storage-uploader/pyproject.toml /app/pyproject.toml
COPY services/s7-storage-uploader/src /app/src
COPY packages/core /app/packages/core

RUN uv sync --no-dev
RUN uv pip install --python /app/.venv/bin/python /app/packages/core

CMD ["uv", "run", "dramatiq", "storage_uploader.worker", "--processes", "1", "--threads", "4", "--queues", "s7-storage-uploader"]
