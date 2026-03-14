import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import settings


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentFile(Base):
    __tablename__ = "document_files"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)


class ChunkStrategy(Base):
    __tablename__ = "chunk_strategies"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    params_json = Column(JSONB, nullable=False, default=dict)
    active = Column(Boolean, default=False)


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False)
    chunk_strategy_id = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmbeddingVersion(Base):
    __tablename__ = "embedding_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    model_id = Column(String, nullable=False)
    dim = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    active = Column(Boolean, default=False)


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(String, primary_key=True, default=generate_uuid)
    chunk_id = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False)
    embedding_version_id = Column(String, nullable=False)
    vector_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MemorySummary(Base):
    __tablename__ = "memory_summaries"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    session_id = Column(String, nullable=False)
    summary_text = Column(Text, nullable=False)
    citations_json = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserKeypoint(Base):
    __tablename__ = "user_keypoints"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    keypoint_text = Column(Text, nullable=False)
    source_session_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvalSet(Base):
    __tablename__ = "eval_sets"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvalItem(Base):
    __tablename__ = "eval_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    eval_set_id = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    ground_truth = Column(Text, nullable=False)
    doc_ids = Column(JSONB, nullable=False, default=list)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, nullable=False)
    strategy_id = Column(String, nullable=False)
    embedding_version_id = Column(String, nullable=False)
    metrics_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
