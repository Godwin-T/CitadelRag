from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.routes.deps import get_current_user, get_db, get_current_org_membership, require_org_admin
from api.db import models
from api.schemas.tenant import TenantCreate, TenantOut
from api.schemas.org import TenantMemberCreate
from api.services.events import record_event

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantOut])
def list_tenants(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    if org_membership.role in {"owner", "admin"}:
        rows = db.query(models.Tenant).filter(models.Tenant.org_id == org_membership.org_id).all()
    else:
        rows = (
            db.query(models.Tenant)
            .join(models.Membership, models.Membership.tenant_id == models.Tenant.id)
            .filter(models.Membership.user_id == user.id, models.Tenant.org_id == org_membership.org_id)
            .all()
        )
    return [TenantOut(id=t.id, name=t.name, slug=t.slug, org_id=t.org_id) for t in rows]


@router.post("", response_model=TenantOut)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(require_org_admin),
):
    existing = (
        db.query(models.Tenant)
        .filter(models.Tenant.slug == payload.slug, models.Tenant.org_id == org_membership.org_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")
    tenant = models.Tenant(name=payload.name, slug=payload.slug, org_id=org_membership.org_id)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    membership = models.Membership(user_id=user.id, tenant_id=tenant.id, role="owner")
    db.add(membership)
    db.commit()
    record_event(
        db,
        tenant.id,
        "tenant_created",
        {"tenant_id": tenant.id, "tenant_name": tenant.name, "actor_user_id": user.id},
    )
    return TenantOut(id=tenant.id, name=tenant.name, slug=tenant.slug, org_id=tenant.org_id)


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    tenant = (
        db.query(models.Tenant)
        .filter(models.Tenant.id == tenant_id, models.Tenant.org_id == org_membership.org_id)
        .first()
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    membership = (
        db.query(models.Membership)
        .filter(models.Membership.user_id == user.id, models.Membership.tenant_id == tenant_id)
        .first()
    )
    if not membership and org_membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Not a member of this tenant")
    return TenantOut(id=tenant.id, name=tenant.name, slug=tenant.slug, org_id=tenant.org_id)


@router.post("/{tenant_id}/members")
def add_tenant_member(
    tenant_id: str,
    payload: TenantMemberCreate,
    db: Session = Depends(get_db),
    org_membership: models.OrgMembership = Depends(require_org_admin),
):
    tenant = (
        db.query(models.Tenant)
        .filter(models.Tenant.id == tenant_id, models.Tenant.org_id == org_membership.org_id)
        .first()
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = (
        db.query(models.Membership)
        .filter(models.Membership.user_id == user.id, models.Membership.tenant_id == tenant_id)
        .first()
    )
    if existing:
        return {"status": "exists"}
    db.add(models.Membership(user_id=user.id, tenant_id=tenant_id, role=payload.role))
    db.commit()
    record_event(
        db,
        tenant.id,
        "tenant_member_added",
        {"tenant_id": tenant.id, "tenant_name": tenant.name, "user_id": user.id, "member_id": payload.user_id, "role": payload.role},
    )
    return {"status": "ok"}
