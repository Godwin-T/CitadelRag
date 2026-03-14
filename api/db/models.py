import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from api.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Membership(Base):
    __tablename__ = "memberships"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), primary_key=True)
    role = Column(String, default="member")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OrgMembership(Base):
    __tablename__ = "org_memberships"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"), primary_key=True)
    role = Column(String, default="member")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    scopes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    title = Column(String, nullable=False)
    title_hash = Column(String, nullable=True)
    source_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentFile(Base):
    __tablename__ = "document_files"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    content_hash = Column(String, nullable=True)


class ChunkStrategy(Base):
    __tablename__ = "chunk_strategies"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    params_json = Column(JSONB, nullable=False, default=dict)
    active = Column(Boolean, default=False)


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    chunk_strategy_id = Column(String, ForeignKey("chunk_strategies.id"), nullable=False)
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
    chunk_id = Column(String, ForeignKey("chunks.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    embedding_version_id = Column(String, ForeignKey("embedding_versions.id"), nullable=False)
    vector_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Query(Base):
    __tablename__ = "queries"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    latency_ms = Column(Integer, default=0)
    no_answer = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String, primary_key=True, default=generate_uuid)
    query_id = Column(String, ForeignKey("queries.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    citations_json = Column(JSONB, nullable=False, default=list)
    faithfulness_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    citations_json = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSettings(Base):
    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_user_settings_user_tenant"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    llm_provider = Column(String, default="groq")
    embed_provider = Column(String, default="openai")
    llm_model = Column(String, nullable=True)
    embed_model = Column(String, nullable=True)
    groq_api_key = Column(String, nullable=True)
    openai_api_key = Column(String, nullable=True)
    lattice_api_key = Column(String, nullable=True)
    chunk_strategy_id = Column(String, ForeignKey("chunk_strategies.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EvalSet(Base):
    __tablename__ = "eval_sets"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvalItem(Base):
    __tablename__ = "eval_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    eval_set_id = Column(String, ForeignKey("eval_sets.id"), nullable=False)
    question = Column(Text, nullable=False)
    ground_truth = Column(Text, nullable=False)
    doc_ids = Column(JSONB, nullable=False, default=list)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    strategy_id = Column(String, ForeignKey("chunk_strategies.id"), nullable=False)
    embedding_version_id = Column(String, ForeignKey("embedding_versions.id"), nullable=False)
    metrics_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    event_type = Column(String, nullable=False)
    payload_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MemorySession(Base):
    __tablename__ = "memory_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MemorySummary(Base):
    __tablename__ = "memory_summaries"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, nullable=False)
    summary_text = Column(Text, nullable=False)
    citations_json = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserKeypoint(Base):
    __tablename__ = "user_keypoints"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    keypoint_text = Column(Text, nullable=False)
    source_session_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"

    id = Column(String, primary_key=True, default=generate_uuid)
    memory_summary_id = Column(String, ForeignKey("memory_summaries.id"), nullable=False)
    embedding_version_id = Column(String, ForeignKey("embedding_versions.id"), nullable=False)
    vector_id = Column(String, nullable=False)
