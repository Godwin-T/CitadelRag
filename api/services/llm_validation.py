from __future__ import annotations

from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def parse_llm_json(raw: str, model: Type[T]) -> T:
    try:
        return model.model_validate_json(raw)
    except ValidationError:
        raise
