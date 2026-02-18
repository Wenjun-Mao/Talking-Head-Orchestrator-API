from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator, List, Optional

from core.logging import configure_service_logger, get_logger

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ingest_nocodb.messaging import enqueue_downstream, enqueue_ping, init_broker
from ingest_nocodb.settings import get_settings


logger = get_logger("s1-ingest-nocodb")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_service_logger("s1-ingest-nocodb", debug=settings.debug_log_payload)
    init_broker(settings)
    yield


app = FastAPI(title="s1-ingest-nocodb", lifespan=lifespan)


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _truncate_text(value: str, *, max_chars: int = 30) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}..."


def _truncate_payload_text_fields(payload: Any, *, max_chars: int = 30) -> Any:
    if isinstance(payload, dict):
        truncated: dict[str, Any] = {}
        for key, value in payload.items():
            if key == "content" and isinstance(value, str):
                truncated[key] = _truncate_text(value, max_chars=max_chars)
            else:
                truncated[key] = _truncate_payload_text_fields(value, max_chars=max_chars)
        return truncated
    if isinstance(payload, list):
        return [_truncate_payload_text_fields(item, max_chars=max_chars) for item in payload]
    return payload


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    logger.bind(
        event="webhook_validation_error",
        stage="s1",
        path=request.url.path,
    ).error("Invalid webhook payload", error_details=error_details)
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid webhook payload."},
    )


class NocoDbRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    record_id: int = Field(gt=0, alias="Id")
    url: NonEmptyStr = Field(alias="url")
    content: NonEmptyStr = Field(alias="content")


class NocoDbWebhookData(BaseModel):
    model_config = ConfigDict(extra="allow")

    table_id: NonEmptyStr
    table_name: Optional[str] = None
    rows: List[NocoDbRow] = Field(min_length=1)


class NocoDbWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    id: str
    version: str
    data: NocoDbWebhookData


class WebhookAck(BaseModel):
    ok: bool
    received_rows: int


@app.post("/ping")
async def ping() -> dict[str, str]:
    settings = get_settings()
    enqueue_ping(settings)
    logger.bind(event="ping_enqueued", stage="s1", queue=settings.downstream_queue).info(
        "Ping enqueued"
    )
    return {"message": "Ping enqueued to s2"}


@app.post("/webhook", response_model=WebhookAck)
async def webhook(payload: NocoDbWebhookPayload) -> WebhookAck:
    settings = get_settings()

    logger.bind(
        event="webhook_received",
        stage="s1",
        table_id=payload.data.table_id,
        received_rows=len(payload.data.rows),
    ).info("Webhook received")

    if settings.debug_log_payload:
        payload_for_log = _truncate_payload_text_fields(payload.model_dump())
        logger.bind(
            event="webhook_payload_debug",
            stage="s1",
            table_id=payload.data.table_id,
        ).info(
            "Received webhook request:\n{}",
            json.dumps(payload_for_log, indent=2, default=str),
        )

    for row in payload.data.rows:
        row_logger = logger.bind(
            event="row_processing",
            stage="s1",
            record_id=row.record_id,
            table_id=payload.data.table_id,
        )

        if settings.debug_log_payload:
            row_for_log = _truncate_payload_text_fields(row.model_dump())
            row_logger.info(
                "Processing row debug payload:\n{}",
                json.dumps(row_for_log, indent=2, default=str),
            )

        enqueue_downstream(
            settings,
            record_id=row.record_id,
            table_id=payload.data.table_id,
            url=row.url,
            content=row.content,
        )
        if settings.debug_log_payload:
            msg_args = {
                "record_id": row.record_id,
                "table_id": payload.data.table_id,
                "url": row.url,
                "content": _truncate_text(row.content),
            }
            row_logger.bind(queue=settings.downstream_queue, event="downstream_enqueued").info(
                "Enqueued downstream message:\n{}",
                json.dumps(msg_args, indent=2, default=str),
            )

    return WebhookAck(ok=True, received_rows=len(payload.data.rows))
