from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="S7_",
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    rabbitmq_url: str = Field(
        ...,
        description="RabbitMQ connection URL",
        validation_alias=AliasChoices("S7_RABBITMQ_URL", "rabbitmq_url"),
    )
    current_queue: str = Field(
        "s7-storage-uploader",
        description="Dramatiq queue consumed by this service",
        validation_alias=AliasChoices("S7_CURRENT_QUEUE", "S7_QUEUE", "current_queue"),
    )
    downstream_queue: str = Field(
        "s8-nocodb-updater",
        description="Dramatiq queue for downstream service",
        validation_alias=AliasChoices("S7_DOWNSTREAM_QUEUE", "downstream_queue"),
    )
    downstream_actor: str = Field(
        "s8_nocodb_updater.process",
        description="Dramatiq actor name for downstream service",
        validation_alias=AliasChoices("S7_DOWNSTREAM_ACTOR", "downstream_actor"),
    )
    chevereto_base_url: str = Field(
        "https://imagor.wanyouwan.cn",
        description="Chevereto base URL",
        validation_alias=AliasChoices("S7_CHEVERETO_BASE_URL", "chevereto_base_url"),
    )
    chevereto_api_key: str = Field(
        ...,
        description="Chevereto API key",
        validation_alias=AliasChoices("S7_CHEVERETO_API_KEY", "chevereto_api_key"),
    )
    chevereto_album_id: str = Field(
        "",
        description="Chevereto album id (set this to route uploads to a specific album)",
        validation_alias=AliasChoices("S7_CHEVERETO_ALBUM_ID", "chevereto_album_id"),
    )
    chevereto_album_name: str = Field(
        "talking head",
        description="Desired album display name for operational reference",
        validation_alias=AliasChoices("S7_CHEVERETO_ALBUM_NAME", "chevereto_album_name"),
    )
    expiration_interval: str = Field(
        "P3D",
        description="Chevereto expiration interval, ISO-8601 duration",
        validation_alias=AliasChoices("S7_EXPIRATION_INTERVAL", "expiration_interval"),
    )
    debug_log_payload: bool = Field(
        False,
        description="Enable verbose logging",
        validation_alias=AliasChoices(
            "DEBUG_LOG_PAYLOAD",
            "debug_log_payload",
            "S7_DEBUG_LOG_PAYLOAD",
        ),
    )


def get_settings() -> Settings:
    return Settings()
