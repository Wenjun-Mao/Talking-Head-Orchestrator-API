FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends ffmpeg \
	&& rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir uv

COPY services/s6-video-compositor/pyproject.toml /app/pyproject.toml
COPY services/s6-video-compositor/src /app/src
COPY packages/core /app/packages/core

RUN uv sync --no-dev
RUN uv pip install --python /app/.venv/bin/python /app/packages/core

CMD ["/bin/sh", "-c", "uv run dramatiq video_compositor.worker -Q ${S6_QUEUE:-s6-video-compositor} -p 1 -t 1"]
