from __future__ import annotations

import json
import os
from typing import Any

import dramatiq
from core.logging import configure_service_logger, get_logger
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from broll_selector.settings import get_settings

settings = get_settings()
configure_service_logger("s5-broll-selector", debug=settings.debug_log_payload)
logger = get_logger("s5-broll-selector")

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.bind(event="worker_init", stage="s5").info(
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
    logger.bind(event="ping", stage="s5", queue=settings.current_queue).info("Worker ping")


@dramatiq.actor(actor_name="s5_broll_selector.process", queue_name=settings.current_queue)
def process(
    record_id: int,
    table_id: str,
    douyin_video_path: str,
    tts_audio_path: str,
    inference_video_path: str,
) -> None:
    settings = get_settings()
    job_logger = logger.bind(
        event="job_received",
        stage="s5",
        record_id=record_id,
        table_id=table_id,
    )
    job_logger.info("Received broll job (pass-through mode)")

    if settings.debug_log_payload:
        payload = {
            "record_id": record_id,
            "table_id": table_id,
            "douyin_video_path": douyin_video_path,
            "tts_audio_path": tts_audio_path,
            "inference_video_path": inference_video_path,
        }
        job_logger.bind(event="job_payload_debug").info(
            "Pass-through payload:\n{}",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

    try:
        _enqueue_downstream(
            settings,
            record_id,
            table_id,
            douyin_video_path,
            tts_audio_path,
            inference_video_path,
        )
        job_logger.bind(event="downstream_enqueued", queue=settings.downstream_queue).info(
            "Pass-through complete"
        )
    except Exception:
        job_logger.bind(event="job_failed").exception("Failed pass-through")
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.bind(event="worker_started", stage="s5").info(
    "Worker started with actors: {}",
    [a.actor_name for a in broker.actors.values()],
)
