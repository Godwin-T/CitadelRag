from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.core.config import TokenData
from api.core.security import decode_token
from api.db.session import get_db
from api.db import models

security = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.User:
    try:
        payload = decode_token(creds.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("missing sub")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_token_data(creds: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    try:
        payload = decode_token(creds.credentials)
        return TokenData(
            user_id=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            org_id=payload.get("org_id"),
            org_role=payload.get("org_role"),
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def get_current_org_membership(
    user: models.User = Depends(get_current_user),
    token: TokenData = Depends(get_token_data),
    db: Session = Depends(get_db),
) -> models.OrgMembership:
    org_id = token.org_id
    if not org_id:
        raise HTTPException(status_code=401, detail="Missing org context")
    membership = (
        db.query(models.OrgMembership)
        .filter(models.OrgMembership.user_id == user.id, models.OrgMembership.org_id == org_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return membership


def require_org_admin(
    membership: models.OrgMembership = Depends(get_current_org_membership),
) -> models.OrgMembership:
    if membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Org admin required")
    return membership


def require_tenant_membership(
    tenant_id: str,
    db: Session,
    user: models.User,
    org_membership: models.OrgMembership,
) -> models.Membership:
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.org_id and tenant.org_id != org_membership.org_id:
        raise HTTPException(status_code=403, detail="Tenant is outside organization")
    membership = (
        db.query(models.Membership)
        .filter(models.Membership.user_id == user.id, models.Membership.tenant_id == tenant_id)
        .first()
    )
    if not membership:
        if org_membership.role in {"owner", "admin"}:
            return models.Membership(user_id=user.id, tenant_id=tenant_id, role="admin")
        raise HTTPException(status_code=403, detail="Not a member of this tenant")
    return membership
