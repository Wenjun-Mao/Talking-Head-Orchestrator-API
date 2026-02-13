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


def get_settings() -> Settings:
    return Settings()
