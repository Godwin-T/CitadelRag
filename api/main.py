from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import time

from api.core.security import hash_password
from api.db.session import SessionLocal
from api.db import models
from api.routes import (
    routes_auth,
    routes_tenants,
    routes_documents,
    routes_query,
    routes_chat,
    routes_users,
    routes_analytics,
    routes_chunk_strategies,
    routes_settings,
    routes_orgs,
    routes_events,
)
from api.services.storage import ensure_bucket_ready
from api.core.config import get_settings
from api.core.logging import setup_logging, set_request_id, get_logger
from alembic import command
from alembic.config import Config

settings = get_settings()

setup_logging()
logger = get_logger()

app = FastAPI(title=settings.app_name)


def _ensure_default_chunk_strategies(db: SessionLocal) -> None:
    existing = {s.name for s in db.query(models.ChunkStrategy).all()}
    defaults = [
        ("fixed", {"max_chars": 1000, "overlap": 100}, True),
        ("recursive", {"max_chars": 1000, "overlap": 100, "separators": ["\n\n", "\n", ". ", " "]}, False),
        ("sentence", {"max_chars": 1000, "overlap": 100, "min_sentence_chars": 20}, False),
        ("paragraph", {"max_chars": 1200, "overlap": 100}, False),
        ("header", {"max_chars": 1500, "overlap": 100, "header_regex": r"^#{1,6}\\s+.+$"}, False),
        ("semantic", {"max_chars": 1200, "overlap": 100, "similarity_threshold": 0.75, "max_sentences": 10}, False),
        ("llm", {"max_chars": 1200, "overlap": 100, "llm_format": "json_list"}, False),
    ]
    for name, params, active in defaults:
        if name in existing:
            continue
        strategy = models.ChunkStrategy(name=name, params_json=params, active=active)
        db.add(strategy)
    db.commit()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]);

app.include_router(routes_auth.router, prefix=settings.api_prefix)
app.include_router(routes_orgs.router, prefix=settings.api_prefix)
app.include_router(routes_tenants.router, prefix=settings.api_prefix)
app.include_router(routes_documents.router, prefix=settings.api_prefix)
app.include_router(routes_query.router, prefix=settings.api_prefix)
app.include_router(routes_query.memory_router, prefix=settings.api_prefix)
app.include_router(routes_chat.router, prefix=settings.api_prefix)
app.include_router(routes_users.router, prefix=settings.api_prefix)
app.include_router(routes_analytics.router, prefix=settings.api_prefix)
app.include_router(routes_analytics.eval_router, prefix=settings.api_prefix)
app.include_router(routes_chunk_strategies.router, prefix=settings.api_prefix)
app.include_router(routes_settings.router, prefix=settings.api_prefix)
app.include_router(routes_events.router, prefix=settings.api_prefix)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = set_request_id()
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.time() - start_time) * 1000
        # logger.info(
        #     "request completed | method={} path={} status={} duration_ms={}",
        #     request.method,
        #     request.url.path,
        #     getattr(response, "status_code", "-"),
        #     round(duration_ms, 2),
        # )

@app.on_event("startup")
def seed_default_admin():
    db = SessionLocal()
    try:
        existing = (
            db.query(models.User)
            .filter(
                (models.User.email == "admin")
                | (models.User.email == "admin@local")
                | (models.User.name == "admin")
            )
            .first()
        )
        if not existing:
            user = models.User(email="admin@local", name="admin", password_hash=hash_password("admin"))
            db.add(user)
            db.commit()
            db.refresh(user)
            existing = user
        else:
            updated = False
            if existing.email == "admin":
                existing.email = "admin@local"
                updated = True
            if existing.name != "admin":
                existing.name = "admin"
                updated = True
            if updated:
                db.commit()
        if existing:
            org = db.query(models.Organization).filter(models.Organization.slug == "default-org").first()
            if not org:
                org = models.Organization(name="Default Organization", slug="default-org")
                db.add(org)
                db.commit()
                db.refresh(org)
            org_membership = (
                db.query(models.OrgMembership)
                .filter(models.OrgMembership.user_id == existing.id, models.OrgMembership.org_id == org.id)
                .first()
            )
            if not org_membership:
                db.add(models.OrgMembership(user_id=existing.id, org_id=org.id, role="owner"))
                db.commit()

            tenant = db.query(models.Tenant).filter(models.Tenant.slug == "default").first()
            if not tenant:
                tenant = models.Tenant(name="Default Workspace", slug="default", org_id=org.id)
                db.add(tenant)
                db.commit()
                db.refresh(tenant)
            elif not tenant.org_id:
                tenant.org_id = org.id
                db.commit()
            membership = (
                db.query(models.Membership)
                .filter(models.Membership.user_id == existing.id, models.Membership.tenant_id == tenant.id)
                .first()
            )
            if not membership:
                db.add(models.Membership(user_id=existing.id, tenant_id=tenant.id, role="owner"))
                db.commit()

            # Backfill existing tenants without org_id
            db.query(models.Tenant).filter(models.Tenant.org_id.is_(None)).update({models.Tenant.org_id: org.id})
            db.commit()
        _ensure_default_chunk_strategies(db)
    finally:
        db.close()


@app.on_event("startup")
def ensure_storage_bucket():
    ensure_bucket_ready()


@app.get("/health")
def health():
    return {"status": "ok"}
