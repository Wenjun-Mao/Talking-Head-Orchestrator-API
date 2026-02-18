from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import dramatiq
from core.logging import configure_service_logger, get_logger
import requests
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from storage_uploader.settings import get_settings

settings = get_settings()
configure_service_logger("s7-storage-uploader", debug=settings.debug_log_payload)
logger = get_logger("s7-storage-uploader")

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.bind(event="worker_init", stage="s7").info(
    "Initializing s7-storage-uploader worker (broker={}, current_queue={}, downstream_queue={}, chevereto_base_url={})",
    _masked_url,
    settings.current_queue,
    settings.downstream_queue,
    settings.chevereto_base_url,
)

if not settings.chevereto_album_id.strip():
    logger.bind(event="album_unset_warning", stage="s7").warning(
        "S7_CHEVERETO_ALBUM_ID is not set; uploads won't be assigned to a specific album (album name '{}' is informational only)",
        settings.chevereto_album_name,
    )

broker = RabbitmqBroker(url=settings.rabbitmq_url)
dramatiq.set_broker(broker)
broker.declare_queue(settings.current_queue, ensure=True)


def _enqueue_downstream(settings: Any, *args: Any) -> None:
    broker = dramatiq.get_broker()
    message = dramatiq.Message(
        queue_name=settings.downstream_queue,
        actor_name=settings.downstream_actor,
        args=list(args),
        kwargs={},
        options={},
    )
    broker.enqueue(message)


def _upload_to_chevereto(
    *,
    base_url: str,
    api_key: str,
    local_video_path: str,
    title: str,
    expiration_interval: str,
    album_id: str,
) -> dict[str, Any]:
    upload_url = f"{base_url.rstrip('/')}/api/1/upload"

    data: dict[str, str] = {
        "format": "json",
        "title": title,
        "expiration": expiration_interval,
    }
    if album_id.strip():
        data["album_id"] = album_id.strip()

    headers = {
        "X-API-Key": api_key,
    }

    with Path(local_video_path).open("rb") as source_file:
        files = {
            "source": (Path(local_video_path).name, source_file, "video/mp4"),
        }
        response = requests.post(upload_url, headers=headers, data=data, files=files, timeout=600)

    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(
            f"Chevereto upload failed with non-JSON response (status={response.status_code}): {response.text[:400]}"
        ) from exc

    if response.status_code != 200 or "image" not in payload:
        raise RuntimeError(
            f"Chevereto upload failed (status={response.status_code}): {json.dumps(payload, ensure_ascii=False)}"
        )

    return payload


@dramatiq.actor(actor_name="s7_storage_uploader.ping", queue_name=settings.current_queue)
def ping() -> None:
    logger.bind(event="ping", stage="s7", queue=settings.current_queue).info("Worker ping")


@dramatiq.actor(actor_name="s7_storage_uploader.process", queue_name=settings.current_queue)
def process(
    record_id: int,
    table_id: str,
    composited_video_path: str,
) -> None:
    settings = get_settings()
    job_logger = logger.bind(
        event="job_received",
        stage="s7",
        record_id=record_id,
        table_id=table_id,
    )
    job_logger.info("Received upload job")

    video_path = Path(composited_video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Composited video not found: {video_path}")

    if settings.debug_log_payload:
        job_logger.bind(event="job_payload_debug").info(
            "Upload inputs: record_id={}, composited_video_path={}, album_id={}, album_name={}, expiration={}",
            record_id,
            composited_video_path,
            settings.chevereto_album_id or "<unset>",
            settings.chevereto_album_name,
            settings.expiration_interval,
        )

    try:
        upload_payload = _upload_to_chevereto(
            base_url=settings.chevereto_base_url,
            api_key=settings.chevereto_api_key,
            local_video_path=str(video_path),
            title=f"record-{record_id}",
            expiration_interval=settings.expiration_interval,
            album_id=settings.chevereto_album_id,
        )

        image = upload_payload["image"]
        public_mp4_url = image.get("url")
        expiration_date_gmt = image.get("expiration_date_gmt")

        if not public_mp4_url:
            raise RuntimeError("Chevereto response missing direct file URL")
        if ".mp4" not in public_mp4_url.lower():
            raise RuntimeError(f"Chevereto response URL is not an mp4 URL: {public_mp4_url}")

        job_logger.bind(
            event="upload_completed",
            public_url=public_mp4_url,
            expiration_date_gmt=expiration_date_gmt,
        ).info("Upload complete")
        _enqueue_downstream(
            settings,
            record_id,
            table_id,
            public_mp4_url,
        )
        job_logger.bind(event="downstream_enqueued", queue=settings.downstream_queue).info(
            "Enqueued downstream message"
        )
    except Exception:
        job_logger.bind(event="job_failed").exception("Failed upload")
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.bind(event="worker_started", stage="s7").info(
    "Worker started with actors: {}",
    [a.actor_name for a in broker.actors.values()],
)
