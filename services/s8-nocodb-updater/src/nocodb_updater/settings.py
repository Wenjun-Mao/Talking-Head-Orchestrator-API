from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="S8_",
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    rabbitmq_url: str = Field(
        ...,
        description="RabbitMQ connection URL",
        validation_alias=AliasChoices("S8_RABBITMQ_URL", "rabbitmq_url"),
    )
    current_queue: str = Field(
        "s8-nocodb-updater",
        description="Dramatiq queue consumed by this service",
        validation_alias=AliasChoices("S8_CURRENT_QUEUE", "S8_QUEUE", "current_queue"),
    )
    nocodb_api_key: str = Field(
        ...,
        description="NocoDB API token for xc-token header",
        validation_alias=AliasChoices("S8_NOCODB_API_KEY", "nocodb_api_key"),
    )
    nocodb_base_url: str = Field(
        ...,
        description="NocoDB base URL, e.g. https://nocodb.example.com",
        validation_alias=AliasChoices("S8_NOCODB_BASE_URL", "nocodb_base_url"),
    )
    nocodb_table_id: str = Field(
        "",
        description="Optional fallback NocoDB table id; runtime webhook table_id is preferred",
        validation_alias=AliasChoices("S8_NOCODB_TABLE_ID", "nocodb_table_id"),
    )
    update_field_name: str = Field(
        "chengpinurl",
        description="NocoDB field name to update with final mp4 URL",
        validation_alias=AliasChoices("S8_UPDATE_FIELD_NAME", "update_field_name"),
    )
    debug_log_payload: bool = Field(
        False,
        description="Enable verbose logging",
        validation_alias=AliasChoices(
            "DEBUG_LOG_PAYLOAD",
            "debug_log_payload",
            "S8_DEBUG_LOG_PAYLOAD",
        ),
    )


def get_settings() -> Settings:
    return Settings()
