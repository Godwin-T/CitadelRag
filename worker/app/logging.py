from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

from loguru import logger

from app.core import settings

job_id_var: ContextVar[str] = ContextVar("job_id", default="-")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="-")
document_id_var: ContextVar[str] = ContextVar("document_id", default="-")


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def _patch_record(record: dict) -> None:
    record["extra"]["job_id"] = job_id_var.get()
    record["extra"]["tenant_id"] = tenant_id_var.get()
    record["extra"]["document_id"] = document_id_var.get()


def setup_logging() -> None:
    logger.remove()
    logger.configure(patcher=_patch_record)
    serialize = bool(settings.log_json)
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level}</level> | "
        "job={extra[job_id]} tenant={extra[tenant_id]} doc={extra[document_id]} | "
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


def set_job_context(job_id: str = "-", tenant_id: str = "-", document_id: str = "-") -> None:
    job_id_var.set(job_id)
    tenant_id_var.set(tenant_id)
    document_id_var.set(document_id)


def clear_job_context() -> None:
    job_id_var.set("-")
    tenant_id_var.set("-")
    document_id_var.set("-")
