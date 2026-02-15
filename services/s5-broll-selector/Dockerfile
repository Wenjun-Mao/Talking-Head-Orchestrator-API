FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir uv

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src

RUN uv sync --no-dev

CMD ["/bin/sh", "-c", "uv run dramatiq broll_selector.worker -Q ${S5_QUEUE:-s5-broll-selector} -p 1 -t 1"]
