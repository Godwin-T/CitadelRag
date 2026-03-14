import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.routes.deps import get_current_user, get_current_org_membership, get_db, require_tenant_membership
from api.core.config import get_settings
from api.db import models
from api.schemas.query import QueryRequest, QueryResponse
from api.schemas.memory import MemorySessionRequest, MemorySessionOut, MemoryUserOut
from api.services.embeddings import embed_texts
from api.prompts.prompts import build_rag_messages, build_highlight_messages
from api.services.llm import generate_answer, score_faithfulness, small_talk_decision
from api.services.memory import load_session_memory, save_session_memory
from api.services.qdrant import search_vectors
from api.services.events import record_event
from api.services.queue import enqueue_memory_summary

from loguru import logger

router = APIRouter(prefix="/query", tags=["query"])
memory_router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=QueryResponse)
def run_query(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(payload.tenant_id, db, user, org_membership)
    settings = get_settings()
    start = time.time()

    session_memory = load_session_memory(payload.tenant_id, payload.session_id)
    summaries = (
        db.query(models.MemorySummary)
        .filter(models.MemorySummary.tenant_id == payload.tenant_id)
        .filter(models.MemorySummary.user_id == user.id)
        .order_by(models.MemorySummary.created_at.desc())
        .limit(5)
        .all()
    )
    keypoints = (
        db.query(models.UserKeypoint)
        .filter(models.UserKeypoint.tenant_id == payload.tenant_id)
        .filter(models.UserKeypoint.user_id == user.id)
        .order_by(models.UserKeypoint.created_at.desc())
        .limit(5)
        .all()
    )

    user_settings = (
        db.query(models.UserSettings)
        .filter(models.UserSettings.user_id == user.id)
        .filter(models.UserSettings.tenant_id == payload.tenant_id)
        .first()
    )

    llm_override = None
    embed_override = None
    if user_settings:
        llm_provider = user_settings.llm_provider or settings.llm_provider
        embed_provider = user_settings.embed_provider or settings.embed_provider
        if embed_provider not in {"openai", "custom"}:
            embed_provider = "openai"
        lattice_key = user_settings.lattice_api_key or ""
        llm_key = ""
        if llm_provider == "custom":
            llm_key = lattice_key
        elif llm_provider == "groq":
            llm_key = user_settings.groq_api_key or ""
        elif llm_provider == "openai":
            llm_key = user_settings.openai_api_key or ""
        else:
            llm_key = user_settings.openai_api_key or user_settings.groq_api_key or ""
        embed_key = ""
        if embed_provider == "custom":
            embed_key = lattice_key
        elif embed_provider == "openai":
            embed_key = user_settings.openai_api_key or ""
        else:
            embed_key = user_settings.openai_api_key or ""

        llm_override = {
            "provider": llm_provider,
            "model": user_settings.llm_model or settings.llm_model,
            "api_key": llm_key,
            "base_url": settings.groq_base_url if llm_provider == "groq" else (
               settings.openai_base_url if llm_provider == "openai" else settings.custom_llm_base_url
            ),
        }
        embed_override = {
            "provider": embed_provider,
            "model": user_settings.embed_model or settings.embed_model,
            "api_key": embed_key,
            "base_url": settings.openai_base_url if embed_provider == "openai" else settings.custom_embed_base_url,
        }

    if settings.small_talk_bypass:
        decision = small_talk_decision(payload.query_text, override=llm_override)
        if decision.get("small_talk") and decision.get("response"):
            record_event(db, payload.tenant_id, "small_talk_bypass", {"query": payload.query_text})
            return QueryResponse(
                query_id="small_talk",
                answer=str(decision.get("response")),
                citations=[],
                no_answer=False,
            )

    highlight_text = (payload.highlight_text or "").strip()
    highlight_mode = (payload.highlight_mode or "").strip()
    highlight_only = highlight_mode == "highlight_only" and bool(highlight_text)

    query_vector = None if highlight_only else embed_texts([payload.query_text], override=embed_override)[0]
    embedding_version_id = payload.embedding_version_id
    if not embedding_version_id:
        active_embedding = db.query(models.EmbeddingVersion).filter(models.EmbeddingVersion.active.is_(True)).first()
        embedding_version_id = active_embedding.id if active_embedding else "default"

    strategy_id = payload.strategy_id
    if not strategy_id:
        if user_settings and user_settings.chunk_strategy_id:
            strategy_id = user_settings.chunk_strategy_id
        else:
            active_strategy = db.query(models.ChunkStrategy).filter(models.ChunkStrategy.active.is_(True)).first()
            strategy_id = active_strategy.id if active_strategy else "default"

    results = []
    if not highlight_only:
        results = search_vectors(
            query_vector,
            filters={
                "tenant_id": payload.tenant_id,
                "embedding_version_id": embedding_version_id,
                "chunk_strategy_id": strategy_id,
                "document_id": payload.document_ids if payload.document_ids else None,
            },
            limit=5,
        )

    citations = []
    sources = []
    for hit in results:
        payload_data = hit.get("payload", {})
        citations.append(
            {
                "chunk_id": payload_data.get("chunk_id"),
                "document_id": payload_data.get("document_id"),
                "score": hit.get("score"),
                "text": payload_data.get("text"),
            }
        )
        if payload_data.get("text"):
            sources.append(payload_data.get("text"))

    memory_context = "\n".join(
        [f"Recent: {m.get('content')}" for m in session_memory][-6:]
        + [f"Summary: {s.summary_text}" for s in summaries]
        + [f"Keypoint: {k.keypoint_text}" for k in keypoints]
    )

    if highlight_text and highlight_mode == "highlight_plus_docs":
        sources = [highlight_text] + sources
        citations = [
            {
                "chunk_id": "highlight",
                "document_id": payload.document_ids[0] if payload.document_ids else None,
                "score": 1.0,
                "text": highlight_text,
                "type": "highlight",
            }
        ] + citations

    if highlight_only:
        messages = build_highlight_messages(highlight_text, payload.query_text, sources)
        citations = [
            {
                "chunk_id": "highlight",
                "document_id": payload.document_ids[0] if payload.document_ids else None,
                "score": 1.0,
                "text": highlight_text,
                "type": "highlight",
            }
        ]
    else:
        messages = build_rag_messages(memory_context, payload.query_text, sources)
    answer_text = generate_answer(messages, citations, override=llm_override)
    max_score = max([c.get("score", 0) for c in citations], default=0)
    no_answer = max_score < 0.2
    faithfulness_score = score_faithfulness(answer_text, sources, override=llm_override)

    query = models.Query(
        tenant_id=payload.tenant_id,
        user_id=user.id,
        query_text=payload.query_text,
        latency_ms=int((time.time() - start) * 1000),
        no_answer=no_answer,
    )
    db.add(query)
    db.commit()
    db.refresh(query)

    answer = models.Answer(
        query_id=query.id,
        answer_text=answer_text,
        citations_json=citations,
        faithfulness_score=faithfulness_score,
    )
    db.add(answer)
    db.commit()

    session_memory.append({"role": "user", "content": payload.query_text})
    session_memory.append({"role": "assistant", "content": answer_text, "citations": citations})
    save_session_memory(payload.tenant_id, payload.session_id, session_memory)

    if len(session_memory) % settings.summary_interval_turns == 0:
        enqueue_memory_summary(
            {
                "tenant_id": payload.tenant_id,
                "user_id": user.id,
                "session_id": payload.session_id,
                "turns": session_memory,
            }
        )

    record_event(db, payload.tenant_id, "query_executed", {"query_id": query.id, "no_answer": no_answer})

    return QueryResponse(query_id=query.id, answer=answer_text, citations=citations, no_answer=no_answer)


@router.get("/{query_id}")
def get_query(
    query_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    query = db.query(models.Query).filter(models.Query.id == query_id).first()
    if not query:
        return {"error": "Not found"}
    require_tenant_membership(query.tenant_id, db, user, org_membership)
    answer = db.query(models.Answer).filter(models.Answer.query_id == query_id).first()
    return {
        "query_id": query.id,
        "query_text": query.query_text,
        "answer": answer.answer_text if answer else "",
        "citations": answer.citations_json if answer else [],
    }


@memory_router.post("/session/start", response_model=MemorySessionOut)
def start_session(
    payload: MemorySessionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(payload.tenant_id, db, user, org_membership)
    session = models.MemorySession(
        tenant_id=payload.tenant_id, user_id=user.id, session_id=payload.session_id
    )
    db.add(session)
    db.commit()
    return MemorySessionOut(session_id=payload.session_id, last_seen_at=str(session.last_seen_at))


@memory_router.post("/session/end", response_model=dict)
def end_session(
    payload: MemorySessionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    session = (
        db.query(models.MemorySession)
        .filter(models.MemorySession.session_id == payload.session_id)
        .filter(models.MemorySession.user_id == user.id)
        .first()
    )
    if session:
        require_tenant_membership(session.tenant_id, db, user, org_membership)
        db.delete(session)
        db.commit()
    return {"status": "ended"}


@memory_router.get("/session/{session_id}", response_model=MemorySessionOut)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    session = (
        db.query(models.MemorySession)
        .filter(models.MemorySession.session_id == session_id)
        .filter(models.MemorySession.user_id == user.id)
        .first()
    )
    if not session:
        return MemorySessionOut(session_id=session_id, last_seen_at="")
    require_tenant_membership(session.tenant_id, db, user, org_membership)
    return MemorySessionOut(session_id=session_id, last_seen_at=str(session.last_seen_at))


@memory_router.get("/user/{user_id}", response_model=MemoryUserOut)
def get_user_memory(
    user_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    if user_id != user.id and org_membership.role not in {"owner", "admin"}:
        return MemoryUserOut(user_id=user_id, summaries=[], keypoints=[])
    summaries = (
        db.query(models.MemorySummary)
        .filter(models.MemorySummary.user_id == user_id)
        .order_by(models.MemorySummary.created_at.desc())
        .limit(10)
        .all()
    )
    keypoints = (
        db.query(models.UserKeypoint)
        .filter(models.UserKeypoint.user_id == user_id)
        .order_by(models.UserKeypoint.created_at.desc())
        .limit(10)
        .all()
    )
    return MemoryUserOut(
        user_id=user_id,
        summaries=[s.summary_text for s in summaries],
        keypoints=[k.keypoint_text for k in keypoints],
    )
