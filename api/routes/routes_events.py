from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import models
from api.routes.deps import get_current_user, get_current_org_membership, get_db
from api.schemas.events import EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(
    limit: int = 20,
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    query = (
        db.query(models.Event, models.Tenant)
        .join(models.Tenant, models.Tenant.id == models.Event.tenant_id)
        .filter(models.Tenant.org_id == org_membership.org_id)
        .order_by(models.Event.created_at.desc())
    )
    if tenant_id:
        query = query.filter(models.Event.tenant_id == tenant_id)
    rows = query.limit(min(limit, 50)).all()
    return [
        EventOut(
            id=event.id,
            tenant_id=event.tenant_id,
            tenant_name=tenant.name,
            event_type=event.event_type,
            payload=event.payload_json or {},
            created_at=event.created_at,
        )
        for event, tenant in rows
    ]
