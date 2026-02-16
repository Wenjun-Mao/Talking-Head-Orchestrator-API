from __future__ import annotations

import os
from typing import Any

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from loguru import logger

from inference_engine.settings import get_settings
from inference_engine.soulx_runtime import SoulXRuntime

# Initialize settings and broker
settings = get_settings()

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.info(
    "Initializing s4-inference-engine worker (broker={}, current_queue={}, downstream_queue={}, model_type={})",
    _masked_url,
    settings.current_queue,
    settings.downstream_queue,
    settings.model_type,
)

broker = RabbitmqBroker(url=settings.rabbitmq_url)
dramatiq.set_broker(broker)
broker.declare_queue(settings.current_queue, ensure=True)

runtime = SoulXRuntime(
    flashhead_ckpt_dir=settings.flashhead_ckpt_dir,
    wav2vec_dir=settings.wav2vec_dir,
    model_type=settings.model_type,
)

if settings.startup_prewarm_enabled:
    logger.info(
        "S4 startup prewarm enabled (duration_sec={})",
        settings.startup_prewarm_duration_sec,
    )
    runtime.prewarm(
        cond_image_path=settings.cond_image_path,
        base_seed=settings.base_seed,
        use_face_crop=settings.use_face_crop,
        duration_sec=settings.startup_prewarm_duration_sec,
    )
else:
    logger.info("S4 startup prewarm disabled")


def _enqueue_downstream(
    settings: Any,
    record_id: int,
    table_id: str,
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
            table_id,
            douyin_video_path,
            tts_audio_path,
            inference_video_path,
        ],
        kwargs={},
        options={},
    )
    broker.enqueue(message)


@dramatiq.actor(actor_name="s4_inference_engine.ping", queue_name=settings.current_queue)
def ping() -> None:
    logger.info("PONG! s4-inference-engine worker is alive.")


@dramatiq.actor(
    actor_name="s4_inference_engine.process",
    queue_name=settings.current_queue,
)
def process(
    record_id: int,
    table_id: str,
    douyin_video_path: str,
    tts_audio_path: str,
) -> None:
    logger.info(f"Received inference job for record_id={record_id}")
    settings = get_settings()

    if settings.debug_log_payload:
        logger.info(
            "Inputs: record_id={}, tts_audio={}, cond_image={}, source_video={}, model_type={}",
            record_id,
            tts_audio_path,
            settings.cond_image_path,
            douyin_video_path,
            settings.model_type,
        )

    try:
        inference_video_path = runtime.generate(
            record_id=record_id,
            cond_image_path=settings.cond_image_path,
            audio_path=tts_audio_path,
            output_dir=settings.output_dir,
            base_seed=settings.base_seed,
            use_face_crop=settings.use_face_crop,
            audio_encode_mode=settings.audio_encode_mode,
        )

        logger.info("SoulX inference complete. Output: {}", inference_video_path)

        # Enqueue for downstream (s5-broll-selector)
        _enqueue_downstream(
            settings,
            record_id=record_id,
            table_id=table_id,
            douyin_video_path=douyin_video_path,
            tts_audio_path=tts_audio_path,
            inference_video_path=inference_video_path,
        )

    except Exception:
        logger.exception(f"Failed SoulX inference for record_id={record_id}")
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.info(f"Worker started with actors: {[a.actor_name for a in broker.actors.values()]}")
