import json
import redis

from api.core.config import get_settings
from api.core.logging import get_logger

_settings = get_settings()
_redis = redis.Redis.from_url(_settings.redis_url, decode_responses=True)
_logger = get_logger()


def enqueue_ingest(payload: dict) -> None:
    _redis.lpush("ingest_queue", json.dumps(payload))
    _logger.info("enqueue ingest | document_id={} tenant_id={}", payload.get("document_id"), payload.get("tenant_id"))


def enqueue_memory_summary(payload: dict) -> None:
    _redis.lpush("memory_queue", json.dumps(payload))
    _logger.info("enqueue memory summary | tenant_id={} session_id={}", payload.get("tenant_id"), payload.get("session_id"))


def enqueue_eval_run(payload: dict) -> None:
    _redis.lpush("eval_queue", json.dumps(payload))
    _logger.info("enqueue eval run | eval_run_id={} tenant_id={}", payload.get("eval_run_id"), payload.get("tenant_id"))
