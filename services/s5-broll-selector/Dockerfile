FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir uv

COPY services/s5-broll-selector/pyproject.toml /app/pyproject.toml
COPY services/s5-broll-selector/src /app/src
COPY packages/core /app/packages/core

RUN uv sync --no-dev
RUN uv pip install --python /app/.venv/bin/python /app/packages/core

CMD ["/bin/sh", "-c", "uv run dramatiq broll_selector.worker -Q ${S5_QUEUE:-s5-broll-selector} -p 1 -t 1"]
