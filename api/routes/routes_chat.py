from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.db import models
from api.routes.deps import get_current_user, get_current_org_membership, get_db, require_tenant_membership
from api.routes.routes_query import run_query
from api.schemas.chat import ChatMessageCreate, ChatMessageOut, ChatSessionCreate, ChatSessionOut
from api.schemas.query import QueryRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionOut)
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(payload.tenant_id, db, user, org_membership)
    session = models.ChatSession(tenant_id=payload.tenant_id, user_id=user.id, title=payload.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatSessionOut(
        id=session.id,
        tenant_id=session.tenant_id,
        user_id=session.user_id,
        title=session.title,
    )


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    rows = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.tenant_id == tenant_id)
        .order_by(models.ChatSession.created_at.desc())
        .all()
    )
    return [ChatSessionOut(id=r.id, tenant_id=r.tenant_id, user_id=r.user_id, title=r.title) for r in rows]


@router.get("/messages", response_model=list[ChatMessageOut])
def list_messages(
    session_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    require_tenant_membership(session.tenant_id, db, user, org_membership)
    rows = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    return [
        ChatMessageOut(
            id=r.id,
            session_id=r.session_id,
            tenant_id=r.tenant_id,
            user_id=r.user_id,
            role=r.role,
            content=r.content,
            citations=r.citations_json,
        )
        for r in rows
    ]


@router.post("/messages", response_model=ChatMessageOut)
def send_message(
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    require_tenant_membership(session.tenant_id, db, user, org_membership)

    user_msg = models.ChatMessage(
        session_id=session.id,
        tenant_id=session.tenant_id,
        user_id=user.id,
        role="user",
        content=payload.message,
        citations_json=[],
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    query_payload = QueryRequest(
        tenant_id=session.tenant_id,
        session_id=session.id,
        query_text=payload.message,
        document_ids=payload.document_ids,
        highlight_text=payload.highlight_text,
        highlight_mode="highlight_only" if payload.highlight_text else None,
    )
    response = run_query(query_payload, db=db, user=user, org_membership=org_membership)

    assistant_msg = models.ChatMessage(
        session_id=session.id,
        tenant_id=session.tenant_id,
        user_id=user.id,
        role="assistant",
        content=response.answer,
        citations_json=response.citations or [],
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatMessageOut(
        id=assistant_msg.id,
        session_id=assistant_msg.session_id,
        tenant_id=assistant_msg.tenant_id,
        user_id=assistant_msg.user_id,
        role=assistant_msg.role,
        content=assistant_msg.content,
        citations=assistant_msg.citations_json,
    )
