from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.routes.deps import get_db
from api.core.security import create_access_token, hash_password, verify_password
from api.core.config import get_settings
from api.db import models
from api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    PasswordResetRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

def _get_default_org(db: Session) -> models.Organization:
    org = db.query(models.Organization).filter(models.Organization.slug == "default-org").first()
    if not org:
        org = models.Organization(name="Default Organization", slug="default-org")
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def _ensure_org_membership(db: Session, user: models.User) -> models.OrgMembership:
    membership = (
        db.query(models.OrgMembership)
        .filter(models.OrgMembership.user_id == user.id)
        .first()
    )
    if membership:
        return membership
    org = _get_default_org(db)
    membership = models.OrgMembership(user_id=user.id, org_id=org.id, role="member")
    db.add(membership)
    db.commit()
    return membership


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=403, detail="Self-registration is disabled. Contact your admin.")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.email.strip()
    user = (
        db.query(models.User)
        .filter(or_(models.User.email == identifier, models.User.name == identifier))
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    org_membership = _ensure_org_membership(db, user)
    token = create_access_token(user.id, None, org_membership.org_id, org_membership.role)
    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    # For MVP, treat refresh_token as a valid access token and re-issue.
    # Replace with proper refresh token storage if needed.
    token = payload.refresh_token
    return TokenResponse(access_token=token)


@router.post("/reset-password")
def reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    row = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token_hash == token_hash)
        .filter(models.PasswordResetToken.used_at.is_(None))
        .filter(models.PasswordResetToken.expires_at > now)
        .first()
    )
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    row.used_at = now
    db.commit()
    return {"status": "ok"}
