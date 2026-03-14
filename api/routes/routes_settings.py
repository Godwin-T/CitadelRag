from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.routes.deps import get_current_user, get_current_org_membership, get_db, require_tenant_membership
from api.core.config import get_settings as get_app_settings
from api.db import models
from api.schemas.settings import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_settings_out(row: models.UserSettings | None, tenant_id: str) -> SettingsOut:
    settings = get_app_settings()
    if not row:
        return SettingsOut(
            tenant_id=tenant_id,
            llm_provider=settings.llm_provider,
            embed_provider=settings.embed_provider,
            llm_model=None,
            embed_model=None,
            chunk_strategy_id=None,
            has_openai_key=False,
            has_groq_key=False,
            has_lattice_key=False,
        )
    return SettingsOut(
        tenant_id=tenant_id,
        llm_provider=row.llm_provider or "groq",
        embed_provider=row.embed_provider or "openai",
        llm_model=row.llm_model,
        embed_model=row.embed_model,
        chunk_strategy_id=row.chunk_strategy_id,
        has_openai_key=bool(row.openai_api_key),
        has_groq_key=bool(row.groq_api_key),
        has_lattice_key=bool(row.lattice_api_key),
    )


@router.get("", response_model=SettingsOut)
def get_settings(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    row = (
        db.query(models.UserSettings)
        .filter(models.UserSettings.user_id == user.id)
        .filter(models.UserSettings.tenant_id == tenant_id)
        .first()
    )
    return _to_settings_out(row, tenant_id)


@router.post("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(payload.tenant_id, db, user, org_membership)
    row = (
        db.query(models.UserSettings)
        .filter(models.UserSettings.user_id == user.id)
        .filter(models.UserSettings.tenant_id == payload.tenant_id)
        .first()
    )
    if not row:
        row = models.UserSettings(user_id=user.id, tenant_id=payload.tenant_id)
        db.add(row)

    if payload.llm_provider is not None:
        row.llm_provider = payload.llm_provider
    if payload.embed_provider is not None:
        row.embed_provider = payload.embed_provider
    if payload.llm_model is not None:
        row.llm_model = payload.llm_model
    if payload.embed_model is not None:
        row.embed_model = payload.embed_model
    if payload.chunk_strategy_id is not None:
        row.chunk_strategy_id = payload.chunk_strategy_id
    if payload.openai_api_key is not None:
        row.openai_api_key = payload.openai_api_key or None
    if payload.groq_api_key is not None:
        row.groq_api_key = payload.groq_api_key or None
    if payload.lattice_api_key is not None:
        row.lattice_api_key = payload.lattice_api_key or None

    db.commit()
    db.refresh(row)
    return _to_settings_out(row, payload.tenant_id)
