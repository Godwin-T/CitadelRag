import uuid
from sqlalchemy.orm import Session

from app.db import SessionLocal, Document, DocumentFile, ChunkStrategy, Chunk, EmbeddingVersion, Embedding, Event
from app.services.extraction import extract_text
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts
from app.services.qdrant import upsert_vectors
from app.logging import get_logger

logger = get_logger()

def _get_default_strategy(db: Session) -> ChunkStrategy:
    strategy = db.query(ChunkStrategy).filter(ChunkStrategy.active.is_(True)).first()
    if strategy:
        return strategy
    strategy = ChunkStrategy(name="fixed", params_json={"max_chars": 1000, "overlap": 100}, active=True)
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def _get_strategy(db: Session, chunk_strategy_id: str | None) -> ChunkStrategy:
    if chunk_strategy_id:
        strategy = db.query(ChunkStrategy).filter(ChunkStrategy.id == chunk_strategy_id).first()
        if strategy:
            return strategy
    return _get_default_strategy(db)


def _get_default_embedding_version(db: Session, dim: int) -> EmbeddingVersion:
    version = db.query(EmbeddingVersion).filter(EmbeddingVersion.active.is_(True)).first()
    if version:
        return version
    version = EmbeddingVersion(name="default", model_id="openai-oss-embed", dim=dim, active=True)
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def ingest_document(
    document_id: str,
    tenant_id: str,
    file_path: str,
    embed_dim: int = 768,
    chunk_strategy_id: str | None = None,
) -> None:
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning(f"document not found | document_id={document_id}")
            return
        logger.info(f"ingest start | document_id={document_id} tenant_id={tenant_id}")
        text = extract_text(file_path)
        logger.info(f"extraction complete | chars={len(text)}")
        strategy = _get_strategy(db, chunk_strategy_id)
        chunks = chunk_text(text, strategy.name, strategy.params_json)
        logger.info(f"chunking complete | count={len(chunks)} strategy={strategy.name}")
        embed_version = _get_default_embedding_version(db, embed_dim)

        vectors = embed_texts([c.text for c in chunks])
        logger.info(f"embedding complete | count={len(vectors)}")
        points = []
        for idx, (chunk_result, vector) in enumerate(zip(chunks, vectors)):
            chunk_text_value = chunk_result.text
            metadata = {
                **(chunk_result.metadata or {}),
                "strategy_name": strategy.name,
                "params_json": strategy.params_json,
                "chunk_index": idx,
            }
            chunk = Chunk(
                document_id=document_id,
                tenant_id=tenant_id,
                chunk_strategy_id=strategy.id,
                text=chunk_text_value,
                metadata_json=metadata,
            )
            db.add(chunk)
            db.commit()
            db.refresh(chunk)

            vector_id = str(uuid.uuid4())
            embedding = Embedding(
                chunk_id=chunk.id,
                tenant_id=tenant_id,
                embedding_version_id=embed_version.id,
                vector_id=vector_id,
            )
            db.add(embedding)
            db.commit()

            points.append(
                {
                    "id": vector_id,
                    "vector": vector,
                    "payload": {
                        "tenant_id": tenant_id,
                        "document_id": document_id,
                        "chunk_id": chunk.id,
                        "embedding_version_id": embed_version.id,
                        "chunk_strategy_id": strategy.id,
                        "text": chunk_text_value,
                    },
                }
            )

        upsert_vectors(points)
        logger.info("qdrant upsert complete | points={}", len(points))
        doc.status = "ready"
        db.commit()
        db.add(
            Event(
                tenant_id=tenant_id,
                event_type="ingestion_completed",
                payload_json={"document_id": document_id, "document_title": doc.title},
            )
        )
        db.commit()
        logger.info("ingest done | document_id={}", document_id)
    finally:
        db.close()
