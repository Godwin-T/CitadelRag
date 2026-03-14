from pydantic import BaseModel
from typing import Any


class ChunkStrategyCreate(BaseModel):
    name: str
    params_json: dict[str, Any] = {}
    active: bool = False


class ChunkStrategyOut(BaseModel):
    id: str
    name: str
    params_json: dict[str, Any]
    active: bool
