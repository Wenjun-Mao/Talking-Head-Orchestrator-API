from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import dramatiq
import requests
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from loguru import logger

from storage_uploader.settings import get_settings

settings = get_settings()

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.info(
    "Initializing s7-storage-uploader worker (broker={}, current_queue={}, downstream_queue={}, chevereto_base_url={})",
    _masked_url,
    settings.current_queue,
    settings.downstream_queue,
    settings.chevereto_base_url,
)

if not settings.chevereto_album_id.strip():
    logger.warning(
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
    logger.info("PONG! s7-storage-uploader worker is alive.")


@dramatiq.actor(actor_name="s7_storage_uploader.process", queue_name=settings.current_queue)
def process(
    record_id: int,
    title: str,
    url: str,
    content: str,
    original_text: str,
    douyin_download_url: str,
    douyin_video_path: str,
    tts_audio_path: str,
    inference_video_path: str,
    composited_video_path: str,
) -> None:
    logger.info("Received upload job for record_id={}", record_id)
    settings = get_settings()

    video_path = Path(composited_video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Composited video not found: {video_path}")

    if settings.debug_log_payload:
        logger.info(
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
            title=title,
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

        logger.info(
            "Upload complete for record_id={}, public_url={}, expiration_date_gmt={}",
            record_id,
            public_mp4_url,
            expiration_date_gmt,
        )
        _enqueue_downstream(
            settings,
            record_id,
            public_mp4_url,
        )
    except Exception:
        logger.exception("Failed upload for record_id={}", record_id)
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.info(f"Worker started with actors: {[a.actor_name for a in broker.actors.values()]}")
