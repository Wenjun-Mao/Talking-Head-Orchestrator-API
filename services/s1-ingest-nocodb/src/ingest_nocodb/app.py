from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator, List, Optional

from loguru import logger

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ingest_nocodb.messaging import enqueue_downstream, enqueue_ping, init_broker
from ingest_nocodb.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_broker(settings)
    yield


app = FastAPI(title="s1-ingest-nocodb", lifespan=lifespan)


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    logger.error("Pydantic validation failed for request to {}: {}", request.url.path, error_details)
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
    return {"message": "Ping enqueued to s2"}


@app.post("/webhook", response_model=WebhookAck)
async def webhook(payload: NocoDbWebhookPayload) -> WebhookAck:
    settings = get_settings()

    if settings.debug_log_payload:
        logger.info(
            "Received webhook request:\n{}",
            json.dumps(payload.model_dump(), indent=2, default=str),
        )

    for row in payload.data.rows:
        if settings.debug_log_payload:
            logger.info(
                "Processing row {}:\n{}",
                row.record_id,
                json.dumps(row.model_dump(), indent=2, default=str),
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
                "content": row.content,
            }
            logger.info(
                "Enqueued downstream message:\n{}",
                json.dumps(msg_args, indent=2, default=str),
            )

    return WebhookAck(ok=True, received_rows=len(payload.data.rows))
