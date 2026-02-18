from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="S6_",
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    rabbitmq_url: str = Field(
        ...,
        description="RabbitMQ connection URL",
        validation_alias=AliasChoices("S6_RABBITMQ_URL", "rabbitmq_url"),
    )
    output_dir: str = Field(
        "/data/s6",
        description="Directory to store composed videos",
        validation_alias=AliasChoices("S6_OUTPUT_DIR", "output_dir"),
    )
    current_queue: str = Field(
        "s6-video-compositor",
        description="Dramatiq queue consumed by this service",
        validation_alias=AliasChoices("S6_CURRENT_QUEUE", "S6_QUEUE", "current_queue"),
    )
    downstream_queue: str = Field(
        "s7-storage-uploader",
        description="Dramatiq queue for downstream service",
        validation_alias=AliasChoices("S6_DOWNSTREAM_QUEUE", "downstream_queue"),
    )
    downstream_actor: str = Field(
        "s7_storage_uploader.process",
        description="Dramatiq actor name for downstream service",
        validation_alias=AliasChoices("S6_DOWNSTREAM_ACTOR", "downstream_actor"),
    )
    overlay_scale_ratio: float = Field(
        0.18,
        description="Foreground scale ratio relative to original size",
        validation_alias=AliasChoices("S6_OVERLAY_SCALE_RATIO", "overlay_scale_ratio"),
    )
    overlay_margin_x: int = Field(
        18,
        description="Foreground left margin in pixels",
        validation_alias=AliasChoices("S6_OVERLAY_MARGIN_X", "overlay_margin_x"),
    )
    overlay_margin_y: int = Field(
        18,
        description="Foreground bottom margin in pixels",
        validation_alias=AliasChoices("S6_OVERLAY_MARGIN_Y", "overlay_margin_y"),
    )
    x264_preset: str = Field(
        "veryfast",
        description="x264 preset when using libx264",
        validation_alias=AliasChoices("S6_X264_PRESET", "x264_preset"),
    )
    x264_crf: int = Field(
        20,
        description="x264 CRF when using libx264",
        validation_alias=AliasChoices("S6_X264_CRF", "x264_crf"),
    )
    target_total_bitrate_mbps: float = Field(
        0.6,
        description="Fallback total bitrate budget in Mbps (video + audio) when reduction is needed",
        validation_alias=AliasChoices(
            "S6_TARGET_TOTAL_BITRATE_MBPS",
            "target_total_bitrate_mbps",
        ),
    )
    min_total_bitrate_mbps: float = Field(
        0.35,
        description="Lowest allowed total bitrate in Mbps before failing",
        validation_alias=AliasChoices(
            "S6_MIN_TOTAL_BITRATE_MBPS",
            "min_total_bitrate_mbps",
        ),
    )
    bitrate_step_kbps: int = Field(
        50,
        description="Step size in kbps when reducing total bitrate across retries",
        validation_alias=AliasChoices("S6_BITRATE_STEP_KBPS", "bitrate_step_kbps"),
    )
    audio_bitrate_kbps: int = Field(
        96,
        description="AAC audio bitrate in kbps for composed output",
        validation_alias=AliasChoices("S6_AUDIO_BITRATE_KBPS", "audio_bitrate_kbps"),
    )
    max_output_size_mb: int = Field(
        30,
        description="Maximum allowed composed output size in MB",
        validation_alias=AliasChoices("S6_MAX_OUTPUT_SIZE_MB", "max_output_size_mb"),
    )
    debug_log_payload: bool = Field(
        False,
        description="Enable verbose logging",
        validation_alias=AliasChoices(
            "DEBUG_LOG_PAYLOAD",
            "debug_log_payload",
            "S6_DEBUG_LOG_PAYLOAD",
        ),
    )


def get_settings() -> Settings:
    return Settings()
