from __future__ import annotations

import sys
from loguru import logger as _logger


def configure_service_logger(service_name: str, *, debug: bool = False) -> None:
    level = "DEBUG" if debug else "INFO"

    _logger.remove()
    _logger.configure(extra={"service": service_name})

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
            "{message} | "
            "{extra}"
        ),
    )


def get_logger(service_name: str | None = None):
    if service_name:
        return _logger.bind(service=service_name)
    return _logger
