from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core import settings

_client = QdrantClient(url=settings.qdrant_url)


def ensure_collection(dim: int | None = None) -> None:
    dim = dim or settings.qdrant_dim
    if _client.collection_exists(settings.qdrant_collection):
        return
    _client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
    )


def upsert_vectors(points: list[dict[str, Any]]) -> None:
    ensure_collection()
    _client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            qmodels.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
            for p in points
        ],
    )


def search_vectors(vector: list[float], filters: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    ensure_collection()
    conditions = []
    for key, value in filters.items():
        conditions.append(qmodels.FieldCondition(key=key, match=qmodels.MatchValue(value=value)))
    query_filter = qmodels.Filter(must=conditions)
    results = _client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        query_filter=query_filter,
        limit=limit,
    )
    return [
        {
            "id": hit.id,
            "score": hit.score,
            "payload": hit.payload,
        }
        for hit in results
    ]
