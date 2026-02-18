from __future__ import annotations

import sys
from loguru import logger as _logger


def _patch_record(record: dict) -> None:
    structured_extra = {k: v for k, v in record["extra"].items() if k != "service"}
    record["extra"]["_structured_suffix"] = f" | {structured_extra}" if structured_extra else ""


def configure_service_logger(service_name: str, *, debug: bool = False) -> None:
    level = "DEBUG" if debug else "INFO"

    _logger.remove()
    _logger.configure(extra={"service": service_name}, patcher=_patch_record)

    _logger.add(
        sys.stderr,
        level=level,
        serialize=False,
        backtrace=False,
        diagnose=False,
        colorize=False,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{extra[service]} | "
            "{message}"
            "{extra[_structured_suffix]}"
        ),
    )


def get_logger(service_name: str | None = None):
    if service_name:
        return _logger.bind(service=service_name)
    return _logger
