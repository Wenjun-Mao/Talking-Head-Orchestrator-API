FROM python:3.10-slim

WORKDIR /app

ENV UV_LINK_MODE=copy

RUN apt-get update \
	&& apt-get install -y --no-install-recommends ffmpeg git build-essential \
	&& rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir uv

COPY services/s4-inference-engine/pyproject.toml /app/pyproject.toml
COPY services/s4-inference-engine/src /app/src
COPY services/s4-inference-engine/vendor /app/vendor
COPY packages/core /app/packages/core

RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev
RUN uv pip install --python /app/.venv/bin/python /app/packages/core

RUN --mount=type=cache,target=/root/.cache/uv uv pip install --python /app/.venv/bin/python --index-url https://download.pytorch.org/whl/cu128 torch==2.7.1 torchvision==0.22.1 \
	&& uv pip install --python /app/.venv/bin/python -r /app/vendor/SoulX-FlashHead/requirements.txt \
	&& uv pip install --python /app/.venv/bin/python ninja wheel
RUN	uv pip install --python /app/.venv/bin/python /app/vendor/flash_attn-2.8.0.post2+cu12torch2.7cxx11abiFALSE-cp310-cp310-linux_x86_64.whl

CMD ["/bin/sh", "-c", "uv run dramatiq inference_engine.worker -Q ${S4_QUEUE:-s4-inference-engine} -p 1 -t 1"]
