from typing import Any
from pydantic import BaseModel


class AnalyticsSeries(BaseModel):
    label: str
    points: list[dict]


class EvalSetCreate(BaseModel):
    tenant_id: str
    name: str
    description: str | None = None


class EvalRunCreate(BaseModel):
    tenant_id: str
    strategy_id: str
    embedding_version_id: str


class EvalRunOut(BaseModel):
    id: str
    metrics: dict[str, Any]
