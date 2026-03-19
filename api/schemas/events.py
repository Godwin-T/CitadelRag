from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class EventOut(BaseModel):
    id: str
    tenant_id: str
    tenant_name: Optional[str] = None
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
