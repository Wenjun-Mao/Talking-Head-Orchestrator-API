FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir uv

COPY services/s3-tts-voice/pyproject.toml /app/pyproject.toml
COPY services/s3-tts-voice/src /app/src
COPY packages/core /app/packages/core

RUN uv sync --no-dev
RUN uv pip install --python /app/.venv/bin/python /app/packages/core

CMD ["/bin/sh", "-c", "uv run dramatiq tts_voice.worker -Q ${S3_QUEUE:-s3-tts-voice} -p 1 -t 1"]
