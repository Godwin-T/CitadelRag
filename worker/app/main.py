import json
import time
import redis

from app.core import settings
from app.jobs.ingest import ingest_document
from app.jobs.memory import summarize_session
from app.jobs.eval import run_eval
from app.logging import setup_logging, get_logger, set_job_context, clear_job_context


redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
setup_logging()
logger = get_logger()


def _pop(queue_name: str):
    item = redis_client.brpop(queue_name, timeout=1)
    if not item:
        return None
    _, payload = item
    return json.loads(payload)


def run_worker():
    logger.info(f"worker started | redis={settings.redis_url}")
    while True:
        payload = _pop("ingest_queue")
        if payload:
            set_job_context(
                job_id=payload.get("document_id", "-"),
                tenant_id=payload.get("tenant_id", "-"),
                document_id=payload.get("document_id", "-"),
            )
            logger.info("ingest job received")
            ingest_document(
                document_id=payload["document_id"],
                tenant_id=payload["tenant_id"],
                file_path=payload["file_path"],
                chunk_strategy_id=payload.get("chunk_strategy_id"),
            )
            logger.info("ingest job completed")
            clear_job_context()

        payload = _pop("memory_queue")
        if payload:
            set_job_context(
                job_id=payload.get("session_id", "-"),
                tenant_id=payload.get("tenant_id", "-"),
                document_id="-",
            )
            logger.info("memory summary job received")
            summarize_session(
                tenant_id=payload["tenant_id"],
                user_id=payload["user_id"],
                session_id=payload["session_id"],
                turns=payload["turns"],
            )
            logger.info("memory summary job completed")
            clear_job_context()

        payload = _pop("eval_queue")
        if payload:
            set_job_context(
                job_id=payload.get("eval_run_id", "-"),
                tenant_id=payload.get("tenant_id", "-"),
                document_id="-",
            )
            logger.info("eval job received")
            run_eval(eval_run_id=payload["eval_run_id"], tenant_id=payload["tenant_id"])
            logger.info("eval job completed")
            clear_job_context()

        time.sleep(0.1)


if __name__ == "__main__":
    run_worker()
