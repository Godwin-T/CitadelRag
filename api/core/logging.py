from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

from loguru import logger

from api.core.config import get_settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def _patch_record(record: dict) -> None:
    record["extra"]["request_id"] = request_id_var.get()


def setup_logging() -> None:
    settings = get_settings()
    logger.remove()
    logger.configure(patcher=_patch_record)
    serialize = bool(settings.log_json)
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level}</level> | "
        "req={extra[request_id]} | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(sys.stdout, level=settings.log_level, serialize=serialize, format=log_format)
    if settings.log_file:
        logger.add(settings.log_file, level=settings.log_level, serialize=serialize, format=log_format)

    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.log_level)


def get_logger():
    return logger


def set_request_id(value: str | None = None) -> str:
    request_id = value or str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id
