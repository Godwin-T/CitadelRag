from pydantic import BaseModel


class MemorySessionRequest(BaseModel):
    tenant_id: str
    session_id: str


class MemorySessionOut(BaseModel):
    session_id: str
    last_seen_at: str


class MemoryUserOut(BaseModel):
    user_id: str
    summaries: list[str]
    keypoints: list[str]
