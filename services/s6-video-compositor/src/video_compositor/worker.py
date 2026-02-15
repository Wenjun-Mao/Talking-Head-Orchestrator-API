from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from loguru import logger

from video_compositor.settings import get_settings

settings = get_settings()

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.info(
    "Initializing s6-video-compositor worker (broker={}, current_queue={}, downstream_queue={})",
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


def _probe_duration_seconds(path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr}")
    return float(result.stdout.strip())


def _compose_video(
    *,
    bg_video_path: str,
    fg_video_path: str,
    tts_audio_path: str,
    output_path: str,
    scale_ratio: float,
    margin_x: int,
    margin_y: int,
) -> None:
    bg_duration = _probe_duration_seconds(bg_video_path)
    fg_duration = _probe_duration_seconds(fg_video_path)
    if fg_duration <= 0:
        raise RuntimeError("Foreground video duration is zero")

    speed_factor = bg_duration / fg_duration
    filter_complex = (
        f"[1:v]setpts=PTS*{speed_factor:.8f},scale=iw*{scale_ratio:.4f}:ih*{scale_ratio:.4f}[fg];"
        f"[0:v][fg]overlay={margin_x}:H-h-{margin_y}:eof_action=pass[vout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        bg_video_path,
        "-i",
        fg_video_path,
        "-i",
        tts_audio_path,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "2:a?",
        "-af",
        "apad",
        "-t",
        f"{bg_duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg compose failed: {result.stderr}")


@dramatiq.actor(actor_name="s6_video_compositor.ping", queue_name=settings.current_queue)
def ping() -> None:
    logger.info("PONG! s6-video-compositor worker is alive.")


@dramatiq.actor(actor_name="s6_video_compositor.process", queue_name=settings.current_queue)
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
) -> None:
    logger.info("Received composition job for record_id={}", record_id)
    settings = get_settings()

    if settings.debug_log_payload:
        payload = {
            "record_id": record_id,
            "background_video": douyin_video_path,
            "foreground_video": inference_video_path,
            "tts_audio": tts_audio_path,
            "scale_ratio": settings.overlay_scale_ratio,
            "margin_x": settings.overlay_margin_x,
            "margin_y": settings.overlay_margin_y,
        }
        logger.info("Composition payload:\n{}", json.dumps(payload, ensure_ascii=False, indent=2))

    try:
        Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
        output_path = str(Path(settings.output_dir) / f"record_{record_id}_{uuid4().hex}_composited.mp4")

        _compose_video(
            bg_video_path=douyin_video_path,
            fg_video_path=inference_video_path,
            tts_audio_path=tts_audio_path,
            output_path=output_path,
            scale_ratio=settings.overlay_scale_ratio,
            margin_x=settings.overlay_margin_x,
            margin_y=settings.overlay_margin_y,
        )

        logger.info("Composition complete for record_id={}, output={}", record_id, output_path)

        _enqueue_downstream(
            settings,
            record_id,
            title,
            url,
            content,
            original_text,
            douyin_download_url,
            douyin_video_path,
            tts_audio_path,
            inference_video_path,
            output_path,
        )
    except Exception:
        logger.exception("Failed composition for record_id={}", record_id)
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.info(f"Worker started with actors: {[a.actor_name for a in broker.actors.values()]}")
