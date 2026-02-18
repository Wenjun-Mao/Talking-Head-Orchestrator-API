from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import dramatiq
import httpx
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from core.logging import configure_service_logger, get_logger

from download_mp4.settings import get_settings


logger = get_logger("s2-download-mp4")

# 1. Initialize Settings and Broker at the top level
# This ensures that when Dramatiq imports this module, the broker is already set
# and any actors defined below will correctly bind to it.
settings = get_settings()
configure_service_logger("s2-download-mp4", debug=settings.debug_log_payload)

# Mask password in URL for safe logging
_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.info(
    "Initializing s2-download-mp4 worker (broker={}, current_queue={}, downstream_queue={})",
    _masked_url,
    settings.current_queue,
    settings.downstream_queue,
)

broker = RabbitmqBroker(url=settings.rabbitmq_url)
dramatiq.set_broker(broker)
broker.declare_queue(settings.current_queue, ensure=True)


def _truncate_text(value: str, *, max_chars: int = 30) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}..."


def _extract_douyin_download_url(payload: dict[str, Any]) -> Optional[str]:
    if isinstance(payload.get("data"), dict):
        data = payload["data"]
        for key in ("url", "download_url", "video_url", "videoUrl", "videoUrls"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    for key in ("url", "download_url", "video_url", "videoUrl", "videoUrls"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _request_douyin_download_url(settings: Any, source_url: str) -> str:
    headers = {"Content-Type": "application/json"}
    body = {"url": source_url, "token": settings.api_token}
    timeout = httpx.Timeout(settings.request_timeout_s)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(settings.api_url, headers=headers, json=body)
        response.raise_for_status()
        payload = response.json()

    if settings.debug_log_payload:
        logger.info(
            "External API response:\n{}",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

    douyin_download_url = _extract_douyin_download_url(payload)
    if not douyin_download_url:
        raise RuntimeError(
            "parseVideoUrl response missing download URL: "
            f"{json.dumps(payload, ensure_ascii=False)[:1000]}"
        )
    return douyin_download_url


def _download_mp4(douyin_download_url: str, output_dir: str, record_id: int) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"record_{record_id}_{uuid4().hex}.mp4"
    target_path = Path(output_dir) / filename
    timeout = httpx.Timeout(120.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream("GET", douyin_download_url) as response:
            response.raise_for_status()
            with target_path.open("wb") as file_handle:
                for chunk in response.iter_bytes():
                    if chunk:
                        file_handle.write(chunk)

    return str(target_path)


def _enqueue_downstream(
    settings: Any,
    record_id: int,
    table_id: str,
    content: str,
    douyin_video_path: str,
) -> None:
    broker = dramatiq.get_broker()
    message = dramatiq.Message(
        queue_name=settings.downstream_queue,
        actor_name=settings.downstream_actor,
        args=[
            record_id,
            table_id,
            content,
            douyin_video_path,
        ],
        kwargs={},
        options={},
    )
    broker.enqueue(message)


@dramatiq.actor(actor_name="s2_download_mp4.ping", queue_name=settings.current_queue)
def ping() -> None:
    logger.bind(event="ping", stage="s2", queue=settings.current_queue).info("Worker ping")


@dramatiq.actor(
    actor_name="s2_download_mp4.process",
    queue_name=settings.current_queue,
)
def process(
    record_id: int,
    table_id: str,
    url: str,
    content: str,
) -> None:
    settings = get_settings()
    job_logger = logger.bind(
        event="job_received",
        stage="s2",
        record_id=record_id,
        table_id=table_id,
    )
    job_logger.info("Received job")

    if settings.debug_log_payload:
        args = {
            "record_id": record_id,
            "table_id": table_id,
            "url": url,
            "content": _truncate_text(content),
        }
        job_logger.bind(event="job_payload_debug").info(
            "Received job details:\n{}",
            json.dumps(args, indent=2, default=str),
        )

    try:
        job_logger.bind(event="download_url_requested").info("Requesting external download URL")
        douyin_download_url = _request_douyin_download_url(settings, url)
        job_logger.bind(event="download_started").info("Downloading MP4")
        douyin_video_path = _download_mp4(
            douyin_download_url,
            settings.output_dir,
            record_id,
        )

        _enqueue_downstream(
            settings,
            record_id=record_id,
            table_id=table_id,
            content=content,
            douyin_video_path=douyin_video_path,
        )
        job_logger.bind(
            event="downstream_enqueued",
            queue=settings.downstream_queue,
        ).info("Enqueued downstream message")

        if settings.debug_log_payload:
            result_args = {
                "record_id": record_id,
                "table_id": table_id,
                "content": _truncate_text(content),
                "douyin_download_url": douyin_download_url,
                "douyin_video_path": douyin_video_path,
                "downstream_queue": settings.downstream_queue,
                "downstream_actor": settings.downstream_actor,
            }
            job_logger.bind(event="job_completed_debug").info(
                "Completed job:\n{}",
                json.dumps(result_args, indent=2, default=str),
            )
    except Exception:
        job_logger.bind(
            event="job_failed",
            record_id=record_id,
            url=url,
        ).exception("Failed job")
        raise
    finally:
        # Ensure all filesystem buffers are flushed to disk (Linux/Unix only; no-op on Windows)
        os.sync() if hasattr(os, "sync") else None


# Log registered actors for verification
logger.bind(event="worker_started", stage="s2").info(
    "Worker started with actors: {}",
    [a.actor_name for a in broker.actors.values()],
)
