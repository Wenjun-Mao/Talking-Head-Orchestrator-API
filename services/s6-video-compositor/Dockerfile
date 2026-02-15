FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends ffmpeg \
	&& rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir uv

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src

RUN uv sync --no-dev

CMD ["/bin/sh", "-c", "uv run dramatiq video_compositor.worker -Q ${S6_QUEUE:-s6-video-compositor} -p 1 -t 1"]
