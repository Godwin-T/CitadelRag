from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
import hashlib
from sqlalchemy.orm import Session

from api.routes.deps import get_current_user, get_current_org_membership, get_db, require_tenant_membership
from api.core.config import get_settings
from api.db import models
from api.schemas.document import DocumentOut, DocumentUploadResponse, DocumentPreviewOut
from api.services.events import record_event
from api.services.queue import enqueue_ingest
from api.services.storage import save_file
from api.core.logging import get_logger

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger()


@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    tenant_id: str = Form(...),
    title: str = Form(...),
    source_type: str = Form(...),
    chunk_strategy_id: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    settings = get_settings()
    logger.info("upload started | tenant_id={} filename={}", tenant_id, file.filename)
    title_hash = hashlib.sha256(title.strip().lower().encode("utf-8")).hexdigest()
    existing = (
        db.query(models.Document)
        .filter(models.Document.tenant_id == tenant_id, models.Document.title_hash == title_hash)
        .first()
    )
    if existing:
        return DocumentUploadResponse(document_id=existing.id, status="duplicate")

    doc = models.Document(
        tenant_id=tenant_id,
        title=title,
        title_hash=title_hash,
        source_type=source_type,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    contents = file.file.read()
    storage_uri = save_file(contents, file.filename)

    doc_file = models.DocumentFile(
        document_id=doc.id,
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(contents),
        storage_path=storage_uri,
    )
    db.add(doc_file)
    db.commit()

    payload = {"document_id": doc.id, "tenant_id": tenant_id, "file_path": storage_uri}
    if not chunk_strategy_id:
        user_settings = (
            db.query(models.UserSettings)
            .filter(models.UserSettings.user_id == user.id)
            .filter(models.UserSettings.tenant_id == tenant_id)
            .first()
        )
        if user_settings and user_settings.chunk_strategy_id:
            chunk_strategy_id = user_settings.chunk_strategy_id
    if chunk_strategy_id:
        payload["chunk_strategy_id"] = chunk_strategy_id
    enqueue_ingest(payload)
    record_event(
        db,
        tenant_id,
        "document_uploaded",
        {"document_id": doc.id, "document_title": doc.title, "source_type": doc.source_type},
    )
    logger.info("upload queued | document_id={} tenant_id={}", doc.id, tenant_id)
    return DocumentUploadResponse(document_id=doc.id, status=doc.status)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    docs = db.query(models.Document).filter(models.Document.tenant_id == tenant_id).all()
    return [DocumentOut(id=d.id, title=d.title, status=d.status, source_type=d.source_type) for d in docs]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    require_tenant_membership(doc.tenant_id, db, user, org_membership)
    return DocumentOut(id=doc.id, title=doc.title, status=doc.status, source_type=doc.source_type)


@router.get("/{document_id}/preview", response_model=DocumentPreviewOut)
def preview_document(
    document_id: str,
    tenant_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == document_id)
        .filter(models.Document.tenant_id == tenant_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = (
        db.query(models.Chunk)
        .filter(models.Chunk.document_id == document_id)
        .order_by(models.Chunk.created_at.asc())
        .all()
    )
    preview_text = "\n\n".join([c.text for c in chunks]) if chunks else ""
    return DocumentPreviewOut(
        document_id=doc.id,
        title=doc.title,
        status=doc.status,
        source_type=doc.source_type,
        preview_text=preview_text,
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    require_tenant_membership(doc.tenant_id, db, user, org_membership)
    db.delete(doc)
    db.commit()
    return {"status": "deleted"}
