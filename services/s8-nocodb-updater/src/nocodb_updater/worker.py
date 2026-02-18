from __future__ import annotations

import json
import os
from typing import Any

import dramatiq
from core.logging import configure_service_logger, get_logger
import requests
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from nocodb_updater.settings import get_settings

settings = get_settings()
configure_service_logger("s8-nocodb-updater", debug=settings.debug_log_payload)
logger = get_logger("s8-nocodb-updater")

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.bind(event="worker_init", stage="s8").info(
    "Initializing s8-nocodb-updater worker (broker={}, current_queue={}, field={})",
    _masked_url,
    settings.current_queue,
    settings.update_field_name,
)

broker = RabbitmqBroker(url=settings.rabbitmq_url)
dramatiq.set_broker(broker)
broker.declare_queue(settings.current_queue, ensure=True)


def _update_record(*, settings: Any, record_id: int, table_id: str, public_mp4_url: str) -> None:
    endpoint = f"{settings.nocodb_base_url.rstrip('/')}/api/v2/tables/{table_id}/records"
    headers = {
        "xc-token": settings.nocodb_api_key,
        "Content-Type": "application/json",
    }
    payload = [
        {
            "Id": record_id,
            settings.update_field_name: public_mp4_url,
        }
    ]

    response = requests.patch(endpoint, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(
            f"NocoDB update failed (status={response.status_code}): {response.text[:500]}"
        )


@dramatiq.actor(actor_name="s8_nocodb_updater.ping", queue_name=settings.current_queue)
def ping() -> None:
    logger.bind(event="ping", stage="s8", queue=settings.current_queue).info("Worker ping")


@dramatiq.actor(actor_name="s8_nocodb_updater.process", queue_name=settings.current_queue)
def process(record_id: int, table_id: str, public_mp4_url: str) -> None:
    settings = get_settings()
    job_logger = logger.bind(
        event="job_received",
        stage="s8",
        record_id=record_id,
        table_id=table_id,
    )
    job_logger.info("Received NocoDB update job")

    if settings.debug_log_payload:
        job_logger.bind(event="job_payload_debug").info(
            "NocoDB update payload: {}",
            json.dumps(
                {
                    "record_id": record_id,
                    "table_id": table_id,
                    "public_mp4_url": public_mp4_url,
                    "field": settings.update_field_name,
                },
                ensure_ascii=False,
            ),
        )

    if ".mp4" not in public_mp4_url.lower():
        raise ValueError(f"Expected mp4 URL, got: {public_mp4_url}")

    try:
        _update_record(
            settings=settings,
            record_id=record_id,
            table_id=table_id,
            public_mp4_url=public_mp4_url,
        )
        job_logger.bind(event="nocodb_update_complete").info("NocoDB update complete")
    except Exception:
        job_logger.bind(event="job_failed").exception("Failed NocoDB update")
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.bind(event="worker_started", stage="s8").info(
    "Worker started with actors: {}",
    [a.actor_name for a in broker.actors.values()],
)
