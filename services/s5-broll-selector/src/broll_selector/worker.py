from __future__ import annotations

import json
import os
from typing import Any

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from loguru import logger

from broll_selector.settings import get_settings

settings = get_settings()

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.info(
    "Initializing s5-broll-selector worker (broker={}, current_queue={}, downstream_queue={})",
    _masked_url,
    settings.current_queue,
    settings.downstream_queue,
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


@dramatiq.actor(actor_name="s5_broll_selector.ping", queue_name=settings.current_queue)
def ping() -> None:
    logger.info("PONG! s5-broll-selector worker is alive.")


@dramatiq.actor(actor_name="s5_broll_selector.process", queue_name=settings.current_queue)
def process(
    record_id: int,
    table_id: str,
    douyin_video_path: str,
    tts_audio_path: str,
    inference_video_path: str,
) -> None:
    logger.info("Received broll job for record_id={} (pass-through mode)", record_id)
    settings = get_settings()

    if settings.debug_log_payload:
        payload = {
            "record_id": record_id,
            "table_id": table_id,
            "douyin_video_path": douyin_video_path,
            "tts_audio_path": tts_audio_path,
            "inference_video_path": inference_video_path,
        }
        logger.info("Pass-through payload:\n{}", json.dumps(payload, ensure_ascii=False, indent=2))

    try:
        _enqueue_downstream(
            settings,
            record_id,
            table_id,
            douyin_video_path,
            tts_audio_path,
            inference_video_path,
        )
        logger.info("Pass-through complete for record_id={}", record_id)
    except Exception:
        logger.exception("Failed pass-through for record_id={}", record_id)
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.info(f"Worker started with actors: {[a.actor_name for a in broker.actors.values()]}")
