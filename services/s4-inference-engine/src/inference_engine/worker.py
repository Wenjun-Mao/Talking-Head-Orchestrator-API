from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from loguru import logger

from inference_engine.settings import get_settings

# Initialize settings and broker
settings = get_settings()

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.info(f"Initializing s4-inference-engine worker (broker={_masked_url})")

broker = RabbitmqBroker(url=settings.rabbitmq_url)
dramatiq.set_broker(broker)


def _enqueue_downstream(
    settings: any,
    record_id: int,
    title: str,
    url: str,
    content: str,
    original_text: str,
    douyin_download_url: str,
    douyin_video_path: str,
    tts_audio_path: str,
    inference_video_path: str,
) -> None:
    broker = dramatiq.get_broker()
    message = dramatiq.Message(
        queue_name=settings.downstream_queue,
        actor_name=settings.downstream_actor,
        args=[
            record_id,
            title,
            url,
            content,
            original_text,
            douyin_download_url,
            douyin_video_path,
            tts_audio_path,
            inference_video_path,
        ],
        kwargs={},
        options={},
    )
    broker.enqueue(message)


@dramatiq.actor(actor_name="s4_inference_engine.ping", queue_name="s4-inference-engine")
def ping() -> None:
    logger.info("PONG! s4-inference-engine worker is alive.")


@dramatiq.actor(
    actor_name="s4_inference_engine.process",
    queue_name="s4-inference-engine",
)
def process(
    record_id: int,
    title: str,
    url: str,
    content: str,
    original_text: str,
    douyin_download_url: str,
    douyin_video_path: str,
    tts_audio_path: str,
) -> None:
    """
    Placeholder worker for the inference engine.
    Currently acts as a pass-through, using the original Douyin video as the 'inference' result.
    """
    logger.info(f"Received inference job for record_id={record_id}")
    settings = get_settings()

    if settings.debug_log_payload:
        logger.info(f"Inputs: record_id={record_id}, tts_audio={tts_audio_path}, source_video={douyin_video_path}")

    try:
        # Placeholder logic: Simply 'copy' the input video to the output directory
        # In a real scenario, this would be where the AI animation happens.
        Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
        filename = f"placeholder_record_{record_id}.mp4"
        inference_video_path = str(Path(settings.output_dir) / filename)
        
        # Simulating work by copying the source video
        shutil.copy2(douyin_video_path, inference_video_path)
        
        logger.info(f"Placeholder inference complete. Output: {inference_video_path}")

        # Enqueue for downstream (s5-broll-selector)
        _enqueue_downstream(
            settings,
            record_id=record_id,
            title=title,
            url=url,
            content=content,
            original_text=original_text,
            douyin_download_url=douyin_download_url,
            douyin_video_path=douyin_video_path,
            tts_audio_path=tts_audio_path,
            inference_video_path=inference_video_path,
        )

    except Exception:
        logger.exception(f"Failed placeholder inference for record_id={record_id}")
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None
