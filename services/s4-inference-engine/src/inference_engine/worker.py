from __future__ import annotations

import os
from typing import Any

import dramatiq
from core.logging import configure_service_logger, get_logger
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from inference_engine.settings import get_settings
from inference_engine.soulx_runtime import SoulXRuntime

# Initialize settings and broker
settings = get_settings()
configure_service_logger("s4-inference-engine", debug=settings.debug_log_payload)
logger = get_logger("s4-inference-engine")

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.bind(event="worker_init", stage="s4").info(
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
    logger.bind(event="startup_prewarm_enabled", stage="s4").info(
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
    logger.bind(event="startup_prewarm_disabled", stage="s4").info("S4 startup prewarm disabled")


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
    logger.bind(event="ping", stage="s4", queue=settings.current_queue).info("Worker ping")


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
    settings = get_settings()
    job_logger = logger.bind(
        event="job_received",
        stage="s4",
        record_id=record_id,
        table_id=table_id,
    )
    job_logger.info("Received inference job")

    if settings.debug_log_payload:
        job_logger.bind(event="job_payload_debug").info(
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

        job_logger.bind(event="inference_completed", inference_video_path=inference_video_path).info(
            "SoulX inference complete"
        )

        # Enqueue for downstream (s5-broll-selector)
        _enqueue_downstream(
            settings,
            record_id=record_id,
            table_id=table_id,
            douyin_video_path=douyin_video_path,
            tts_audio_path=tts_audio_path,
            inference_video_path=inference_video_path,
        )
        job_logger.bind(event="downstream_enqueued", queue=settings.downstream_queue).info(
            "Enqueued downstream message"
        )

    except Exception:
        job_logger.bind(event="job_failed").exception("Failed SoulX inference")
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.bind(event="worker_started", stage="s4").info(
    "Worker started with actors: {}",
    [a.actor_name for a in broker.actors.values()],
)
