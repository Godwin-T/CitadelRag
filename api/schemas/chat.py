from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    tenant_id: str
    title: str | None = None


class ChatSessionOut(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    title: str | None = None


class ChatMessageCreate(BaseModel):
    tenant_id: str
    session_id: str
    message: str
    document_ids: list[str] | None = None
    highlight_text: str | None = None


class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    tenant_id: str
    user_id: str
    role: str
    content: str
    citations: list[dict] | None = None
