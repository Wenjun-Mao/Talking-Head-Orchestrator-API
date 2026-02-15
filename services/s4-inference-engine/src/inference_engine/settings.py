from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="S4_",
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    rabbitmq_url: str = Field(
        ...,
        description="RabbitMQ connection URL",
        validation_alias=AliasChoices("S4_RABBITMQ_URL", "rabbitmq_url"),
    )
    output_dir: str = Field(
        "/data/s4",
        description="Directory to store inference results",
        validation_alias=AliasChoices("S4_OUTPUT_DIR", "output_dir"),
    )
    current_queue: str = Field(
        "s4-inference-engine",
        description="Dramatiq queue consumed by this service",
        validation_alias=AliasChoices(
            "S4_CURRENT_QUEUE",
            "S4_QUEUE",
            "current_queue",
        ),
    )
    downstream_queue: str = Field(
        "s5-broll-selector",
        description="Dramatiq queue for downstream service",
        validation_alias=AliasChoices("S4_DOWNSTREAM_QUEUE", "downstream_queue"),
    )
    downstream_actor: str = Field(
        "s5_broll_selector.process",
        description="Dramatiq actor name for downstream service",
        validation_alias=AliasChoices("S4_DOWNSTREAM_ACTOR", "downstream_actor"),
    )
    debug_log_payload: bool = Field(
        False,
        description="Enable verbose logging",
        validation_alias=AliasChoices(
            "DEBUG_LOG_PAYLOAD",
            "debug_log_payload",
            "S4_DEBUG_LOG_PAYLOAD",
        ),
    )
    flashhead_ckpt_dir: str = Field(
        "/models/SoulX-FlashHead-1_3B",
        description="Local path to SoulX-FlashHead checkpoint directory",
        validation_alias=AliasChoices(
            "S4_FLASHHEAD_CKPT_DIR",
            "flashhead_ckpt_dir",
        ),
    )
    wav2vec_dir: str = Field(
        "/models/wav2vec2-base-960h",
        description="Local path to wav2vec2 checkpoint directory",
        validation_alias=AliasChoices(
            "S4_WAV2VEC_DIR",
            "wav2vec_dir",
        ),
    )
    model_type: str = Field(
        "lite",
        description="SoulX model type: pro or lite",
        validation_alias=AliasChoices("S4_MODEL_TYPE", "model_type"),
    )
    cond_image_path: str = Field(
        "/data/imgs/girl.png",
        description="Condition image used by SoulX inference",
        validation_alias=AliasChoices("S4_COND_IMAGE_PATH", "cond_image_path"),
    )
    audio_encode_mode: str = Field(
        "stream",
        description="Audio encode mode: stream or once",
        validation_alias=AliasChoices("S4_AUDIO_ENCODE_MODE", "audio_encode_mode"),
    )
    use_face_crop: bool = Field(
        False,
        description="Enable face crop for extracted condition image",
        validation_alias=AliasChoices("S4_USE_FACE_CROP", "use_face_crop"),
    )
    base_seed: int = Field(
        42,
        description="Seed used by SoulX pipeline",
        validation_alias=AliasChoices("S4_BASE_SEED", "base_seed"),
    )
    startup_prewarm_enabled: bool = Field(
        True,
        description="Run one startup warmup pass to trigger Torch compile before first real job",
        validation_alias=AliasChoices("S4_STARTUP_PREWARM_ENABLED", "startup_prewarm_enabled"),
    )
    startup_prewarm_duration_sec: int = Field(
        8,
        description="Warmup audio length in seconds used for startup prewarm",
        validation_alias=AliasChoices("S4_STARTUP_PREWARM_DURATION_SEC", "startup_prewarm_duration_sec"),
        ge=2,
        le=60,
    )


def get_settings() -> Settings:
    return Settings()
