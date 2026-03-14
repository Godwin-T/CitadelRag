import math
from sqlalchemy.orm import Session

from app.db import SessionLocal, EvalRun, EvalItem
from app.services.embeddings import embed_texts
from app.services.qdrant import search_vectors


def _recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = set(retrieved[:k])
    return len(top_k.intersection(relevant)) / len(relevant)


def _mrr(retrieved: list[str], relevant: set[str]) -> float:
    for idx, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / idx
    return 0.0


def _ndcg(retrieved: list[str], relevant: set[str], k: int) -> float:
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            dcg += 1.0 / math.log2(i + 1)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / idcg if idcg else 0.0


def run_eval(eval_run_id: str, tenant_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.query(EvalRun).filter(EvalRun.id == eval_run_id).first()
        if not run:
            return
        items = db.query(EvalItem).all()
        recalls = []
        mrrs = []
        ndcgs = []
        for item in items:
            query_vector = embed_texts([item.question])[0]
            results = search_vectors(
                query_vector,
                filters={"tenant_id": tenant_id},
                limit=5,
            )
            retrieved = [hit.get("payload", {}).get("document_id") for hit in results]
            relevant = set(item.doc_ids or [])
            recalls.append(_recall_at_k(retrieved, relevant, 5))
            mrrs.append(_mrr(retrieved, relevant))
            ndcgs.append(_ndcg(retrieved, relevant, 5))
        metrics = {
            "recall@5": sum(recalls) / len(recalls) if recalls else 0.0,
            "mrr": sum(mrrs) / len(mrrs) if mrrs else 0.0,
            "ndcg@5": sum(ndcgs) / len(ndcgs) if ndcgs else 0.0,
        }
        run.metrics_json = metrics
        db.commit()
    finally:
        db.close()
