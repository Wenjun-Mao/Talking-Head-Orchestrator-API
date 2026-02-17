from __future__ import annotations

import sys
from loguru import logger as _logger


def configure_service_logger(service_name: str, *, debug: bool = False) -> None:
    level = "DEBUG" if debug else "INFO"
    _logger.remove()
    _logger.configure(extra={"service": service_name})
    _logger.add(
        sys.stdout,
        level=level,
        serialize=True,
        backtrace=False,
        diagnose=False,
    )


def get_logger(service_name: str | None = None):
    if service_name:
        return _logger.bind(service=service_name)
    return _logger
