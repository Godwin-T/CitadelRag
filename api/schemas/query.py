from pydantic import BaseModel
from typing import Any


class QueryRequest(BaseModel):
    tenant_id: str
    session_id: str
    query_text: str
    strategy_id: str | None = None
    embedding_version_id: str | None = None
    document_ids: list[str] | None = None
    highlight_text: str | None = None
    highlight_mode: str | None = None


class QueryResponse(BaseModel):
    query_id: str
    answer: str
    citations: list[dict[str, Any]]
    no_answer: bool


class SmallTalkDecision(BaseModel):
    small_talk: bool
    response: str
