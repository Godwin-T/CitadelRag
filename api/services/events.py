from sqlalchemy.orm import Session
from api.db import models


def record_event(db: Session, tenant_id: str, event_type: str, payload: dict) -> None:
    event = models.Event(tenant_id=tenant_id, event_type=event_type, payload_json=payload)
    db.add(event)
    db.commit()
