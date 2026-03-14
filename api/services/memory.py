import json
from typing import Any
import redis

from api.core.config import get_settings

_settings = get_settings()
_redis = redis.Redis.from_url(_settings.redis_url, decode_responses=True)


def memory_key(tenant_id: str, session_id: str) -> str:
    return f"memory:{tenant_id}:{session_id}"


def load_session_memory(tenant_id: str, session_id: str) -> list[dict[str, Any]]:
    data = _redis.get(memory_key(tenant_id, session_id))
    if not data:
        return []
    try:
        return json.loads(data)
    except Exception:
        return []


def save_session_memory(tenant_id: str, session_id: str, turns: list[dict[str, Any]]) -> None:
    _redis.set(memory_key(tenant_id, session_id), json.dumps(turns), ex=_settings.memory_ttl_seconds)
