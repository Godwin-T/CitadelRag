from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.core.config import get_settings
from api.core.security import hash_password
from api.db import models
from api.routes.deps import get_db, require_org_admin
from api.schemas.auth import PasswordResetLink
from api.schemas.user import UserCreate, UserOut
from api.services.events import record_event

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=PasswordResetLink)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    org_membership: models.OrgMembership = Depends(require_org_admin),
):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    temp_password = payload.temp_password or secrets.token_urlsafe(12)
    user = models.User(email=payload.email, name=payload.name, password_hash=hash_password(temp_password))
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(models.OrgMembership(user_id=user.id, org_id=org_membership.org_id, role="member"))
    db.commit()

    tenant = (
        db.query(models.Tenant)
        .filter(models.Tenant.org_id == org_membership.org_id)
        .order_by(models.Tenant.created_at.asc())
        .first()
    )
    if tenant:
        record_event(
            db,
            tenant.id,
            "user_created",
            {"user_id": user.id, "user_email": user.email, "user_name": user.name, "tenant_id": tenant.id},
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=get_settings().password_reset_ttl_minutes)
    db.add(
        models.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    db.commit()

    reset_link = f"{get_settings().password_reset_base_url}?token={raw_token}"
    return PasswordResetLink(user_id=user.id, reset_link=reset_link)


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    org_membership: models.OrgMembership = Depends(require_org_admin),
):
    rows = (
        db.query(models.User)
        .join(models.OrgMembership, models.OrgMembership.user_id == models.User.id)
        .filter(models.OrgMembership.org_id == org_membership.org_id)
        .order_by(models.User.name.asc())
        .all()
    )
    return [UserOut(id=u.id, email=u.email, name=u.name) for u in rows]
