from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

import dramatiq
from core.logging import configure_service_logger, get_logger
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from video_compositor.settings import get_settings

settings = get_settings()
configure_service_logger("s6-video-compositor", debug=settings.debug_log_payload)
logger = get_logger("s6-video-compositor")

_url_parts = settings.rabbitmq_url.split("@")
_masked_url = _url_parts[-1] if len(_url_parts) > 1 else settings.rabbitmq_url

logger.bind(event="worker_init", stage="s6").info(
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


def _probe_video_fps(path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate,r_frame_rate",
        "-of",
        "json",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe fps probe failed for {path}: {result.stderr}")

    payload = json.loads(result.stdout)
    streams = payload.get("streams", [])
    if not streams:
        return 25.0

    def _parse_rate(rate: str) -> float:
        if not rate or rate == "0/0":
            return 0.0
        if "/" in rate:
            num_str, den_str = rate.split("/", 1)
            num = float(num_str)
            den = float(den_str)
            return num / den if den > 0 else 0.0
        return float(rate)

    avg = _parse_rate(streams[0].get("avg_frame_rate", "0/0"))
    raw = _parse_rate(streams[0].get("r_frame_rate", "0/0"))
    fps = avg if avg > 0 else raw
    return fps if fps > 0 else 25.0


def _probe_total_bitrate_kbps(path: str) -> int:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=bit_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe bitrate probe failed for {path}: {result.stderr}")

    value = result.stdout.strip()
    if not value:
        return 0

    try:
        return max(0, int(round(float(value) / 1000)))
    except ValueError:
        return 0


def _compose_video(
    *,
    bg_video_path: str,
    fg_video_path: str,
    tts_audio_path: str,
    output_path: str,
    scale_ratio: float,
    margin_x: int,
    margin_y: int,
    x264_preset: str,
    x264_crf: int,
    target_total_bitrate_mbps: float,
    min_total_bitrate_mbps: float,
    bitrate_step_kbps: int,
    audio_bitrate_kbps: int,
    max_output_size_mb: int,
) -> None:
    bg_duration = _probe_duration_seconds(bg_video_path)
    fg_duration = _probe_duration_seconds(fg_video_path)
    bg_fps = _probe_video_fps(bg_video_path)
    bg_total_kbps = _probe_total_bitrate_kbps(bg_video_path)

    if bg_duration <= 0:
        raise RuntimeError("Background video duration is zero")
    if fg_duration <= 0:
        raise RuntimeError("Foreground video duration is zero")

    target_duration = fg_duration
    bg_setpts_factor = target_duration / bg_duration
    is_slowdown = bg_setpts_factor > 1.0001
    bg_chain = f"[0:v]setpts=PTS*{bg_setpts_factor:.8f},fps={bg_fps:.6f}:round=near[bg]"

    fallback_total_kbps = max(100, int(round(target_total_bitrate_mbps * 1000)))
    min_total_kbps = max(100, int(round(min_total_bitrate_mbps * 1000)))
    step_kbps = max(10, bitrate_step_kbps)
    start_total_kbps = max(100, bg_total_kbps) if bg_total_kbps > 0 else fallback_total_kbps

    filter_complex = (
        f"{bg_chain};"
        f"[1:v]setpts=PTS-STARTPTS,scale=iw*{scale_ratio:.4f}:ih*{scale_ratio:.4f}[fg];"
        f"[bg][fg]overlay={margin_x}:H-h-{margin_y}:eof_action=pass:shortest=0[vout]"
    )

    logger.info(
        "S6 duration reconcile: s2={:.3f}s, s4={:.3f}s (target), bg_setpts_factor={:.6f}, mode={}",
        bg_duration,
        fg_duration,
        bg_setpts_factor,
        "slow_down_s2" if is_slowdown else "speed_up_s2",
    )

    logger.info(
        "S6 bitrate strategy: s2_total={} kbps, initial_total={} kbps, fallback_total={} kbps, min_total={} kbps, step={} kbps, max_output={} MB",
        bg_total_kbps,
        start_total_kbps,
        fallback_total_kbps,
        min_total_kbps,
        step_kbps,
        max_output_size_mb,
    )

    attempt_total_kbps = start_total_kbps
    attempt_idx = 0

    while True:
        attempt_idx += 1
        target_audio_kbps = min(max(32, audio_bitrate_kbps), max(32, attempt_total_kbps - 100))
        target_video_kbps = max(100, attempt_total_kbps - target_audio_kbps)

        common_cmd = [
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
            f"{target_duration:.3f}",
            "-fps_mode",
            "cfr",
            "-r",
            f"{bg_fps:.6f}",
            "-c:v",
            "libx264",
            "-preset",
            x264_preset,
            "-crf",
            str(x264_crf),
            "-b:v",
            f"{target_video_kbps}k",
            "-maxrate",
            f"{target_video_kbps}k",
            "-bufsize",
            f"{target_video_kbps * 2}k",
            "-c:a",
            "aac",
            "-b:a",
            f"{target_audio_kbps}k",
            "-movflags",
            "+faststart",
            output_path,
        ]

        logger.info(
            "S6 encode attempt #{}: total={} kbps (video={} kbps, audio={} kbps)",
            attempt_idx,
            attempt_total_kbps,
            target_video_kbps,
            target_audio_kbps,
        )

        result = subprocess.run(common_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg compose failed: {result.stderr}")

        output_size_bytes = Path(output_path).stat().st_size
        output_size_mb = output_size_bytes / (1024 * 1024)
        if output_size_mb <= max_output_size_mb:
            return

        logger.warning(
            "S6 encode oversize on attempt #{}: {:.2f} MB > {} MB at total={} kbps",
            attempt_idx,
            output_size_mb,
            max_output_size_mb,
            attempt_total_kbps,
        )

        if attempt_total_kbps <= min_total_kbps:
            raise RuntimeError(
                "ffmpeg compose exceeded max output size even at minimum bitrate: "
                f"{output_size_mb:.2f} MB > {max_output_size_mb} MB (min_total={min_total_kbps} kbps)"
            )

        if attempt_total_kbps > fallback_total_kbps:
            next_total_kbps = max(min_total_kbps, fallback_total_kbps)
        else:
            next_total_kbps = max(min_total_kbps, attempt_total_kbps - step_kbps)

        if next_total_kbps >= attempt_total_kbps:
            raise RuntimeError(
                "Unable to reduce bitrate further while output remains oversized: "
                f"{output_size_mb:.2f} MB > {max_output_size_mb} MB"
            )

        attempt_total_kbps = next_total_kbps


@dramatiq.actor(actor_name="s6_video_compositor.ping", queue_name=settings.current_queue)
def ping() -> None:
    logger.bind(event="ping", stage="s6", queue=settings.current_queue).info("Worker ping")


@dramatiq.actor(actor_name="s6_video_compositor.process", queue_name=settings.current_queue)
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
        stage="s6",
        record_id=record_id,
        table_id=table_id,
    )
    job_logger.info("Received composition job")

    if settings.debug_log_payload:
        payload = {
            "record_id": record_id,
            "table_id": table_id,
            "background_video": douyin_video_path,
            "foreground_video": inference_video_path,
            "tts_audio": tts_audio_path,
            "scale_ratio": settings.overlay_scale_ratio,
            "margin_x": settings.overlay_margin_x,
            "margin_y": settings.overlay_margin_y,
        }
        job_logger.bind(event="job_payload_debug").info(
            "Composition payload:\n{}",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

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
            x264_preset=settings.x264_preset,
            x264_crf=settings.x264_crf,
            target_total_bitrate_mbps=settings.target_total_bitrate_mbps,
            min_total_bitrate_mbps=settings.min_total_bitrate_mbps,
            bitrate_step_kbps=settings.bitrate_step_kbps,
            audio_bitrate_kbps=settings.audio_bitrate_kbps,
            max_output_size_mb=settings.max_output_size_mb,
        )

        job_logger.bind(event="composition_completed", output_path=output_path).info(
            "Composition complete"
        )

        _enqueue_downstream(
            settings,
            record_id,
            table_id,
            output_path,
        )
        job_logger.bind(event="downstream_enqueued", queue=settings.downstream_queue).info(
            "Enqueued downstream message"
        )
    except Exception:
        job_logger.bind(event="job_failed").exception("Failed composition")
        raise
    finally:
        os.sync() if hasattr(os, "sync") else None


logger.bind(event="worker_started", stage="s6").info(
    "Worker started with actors: {}",
    [a.actor_name for a in broker.actors.values()],
)
