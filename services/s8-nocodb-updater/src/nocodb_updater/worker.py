from __future__ import annotations

import json
import os
from typing import Any

import dramatiq
import requests
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from loguru import logger

from nocodb_updater.settings import get_settings

settings = get_settings()

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.info(
    "Initializing s8-nocodb-updater worker (broker={}, current_queue={}, fallback_table_id={}, field={})",
    _masked_url,
    settings.current_queue,
    settings.nocodb_table_id,
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
    logger.info("PONG! s8-nocodb-updater worker is alive.")


@dramatiq.actor(actor_name="s8_nocodb_updater.process", queue_name=settings.current_queue)
def process(record_id: int, table_id: str, public_mp4_url: str = "", *extra_args: Any) -> None:
    logger.info("Received NocoDB update job for record_id={}", record_id)
    settings = get_settings()

    incoming_values: list[Any] = [table_id, public_mp4_url, *extra_args]
    resolved_table_id = ""
    resolved_public_mp4_url = ""

    for candidate in incoming_values:
        if isinstance(candidate, str) and ".mp4" in candidate.lower():
            resolved_public_mp4_url = candidate
            break

    for candidate in incoming_values:
        if not isinstance(candidate, str):
            continue
        normalized = candidate.strip()
        if not normalized:
            continue
        if normalized == resolved_public_mp4_url:
            continue
        resolved_table_id = normalized
        break

    if not resolved_table_id and settings.nocodb_table_id.strip():
        resolved_table_id = settings.nocodb_table_id.strip()

    if settings.debug_log_payload:
        logger.info(
            "NocoDB update payload: {}",
            json.dumps(
                {
                    "record_id": record_id,
                    "table_id": resolved_table_id,
                    "public_mp4_url": resolved_public_mp4_url,
                    "field": settings.update_field_name,
                    "fallback_table_id": settings.nocodb_table_id,
                },
                ensure_ascii=False,
            ),
        )

    if not resolved_table_id:
        raise ValueError("Missing table_id in message and no S8_NOCODB_TABLE_ID fallback configured")

    if ".mp4" not in resolved_public_mp4_url.lower():
        raise ValueError(f"Expected mp4 URL, got: {resolved_public_mp4_url}")

    try:
        _update_record(
            settings=settings,
            record_id=record_id,
            table_id=resolved_table_id,
            public_mp4_url=resolved_public_mp4_url,
        )
        logger.info("NocoDB update complete for record_id={}", record_id)
    except Exception:
        logger.exception("Failed NocoDB update for record_id={}", record_id)
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.info(f"Worker started with actors: {[a.actor_name for a in broker.actors.values()]}")
