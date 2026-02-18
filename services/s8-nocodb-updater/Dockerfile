FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir uv

COPY services/s8-nocodb-updater/pyproject.toml /app/pyproject.toml
COPY services/s8-nocodb-updater/src /app/src
COPY packages/core /app/packages/core

RUN uv sync --no-dev
RUN uv pip install --python /app/.venv/bin/python /app/packages/core

CMD ["uv", "run", "dramatiq", "nocodb_updater.worker", "--processes", "1", "--threads", "4", "--queues", "s8-nocodb-updater"]
