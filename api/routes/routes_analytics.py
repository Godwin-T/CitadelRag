import csv
import json
from io import StringIO
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.routes.deps import get_current_user, get_current_org_membership, get_db, require_tenant_membership
from api.db import models
from api.schemas.analytics import EvalRunCreate, EvalRunOut
from api.services.queue import enqueue_eval_run

router = APIRouter(prefix="/analytics", tags=["analytics"])
eval_router = APIRouter(prefix="/eval", tags=["eval"])


@router.get("/queries")
def query_volume(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    count = db.query(func.count(models.Query.id)).filter(models.Query.tenant_id == tenant_id).scalar() or 0
    return {"count": count}


@router.get("/latency")
def latency_stats(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    avg = db.query(func.avg(models.Query.latency_ms)).filter(models.Query.tenant_id == tenant_id).scalar() or 0
    return {"avg_ms": int(avg)}


@router.get("/no-answer")
def no_answer_rate(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    total = db.query(func.count(models.Query.id)).filter(models.Query.tenant_id == tenant_id).scalar() or 0
    no_answer = (
        db.query(func.count(models.Query.id))
        .filter(models.Query.tenant_id == tenant_id)
        .filter(models.Query.no_answer.is_(True))
        .scalar()
        or 0
    )
    rate = (no_answer / total) if total else 0
    return {"rate": rate}


@eval_router.post("/sets")
def create_eval_set(
    tenant_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(tenant_id, db, user, org_membership)
    eval_set = models.EvalSet(tenant_id=tenant_id, name=name, description=description)
    db.add(eval_set)
    db.commit()
    db.refresh(eval_set)

    contents = file.file.read().decode("utf-8")
    reader = csv.DictReader(StringIO(contents))
    for row in reader:
        raw_doc_ids = row.get("doc_ids", "[]")
        try:
            doc_ids = json.loads(raw_doc_ids) if isinstance(raw_doc_ids, str) else raw_doc_ids
        except json.JSONDecodeError:
            doc_ids = []
        item = models.EvalItem(
            eval_set_id=eval_set.id,
            question=row.get("question", ""),
            ground_truth=row.get("ground_truth", ""),
            doc_ids=doc_ids,
        )
        db.add(item)
    db.commit()
    return {"eval_set_id": eval_set.id}


@eval_router.post("/runs", response_model=EvalRunOut)
def run_eval(
    payload: EvalRunCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    require_tenant_membership(payload.tenant_id, db, user, org_membership)
    run = models.EvalRun(
        tenant_id=payload.tenant_id,
        strategy_id=payload.strategy_id,
        embedding_version_id=payload.embedding_version_id,
        metrics_json={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    enqueue_eval_run({"eval_run_id": run.id, "tenant_id": payload.tenant_id})
    return EvalRunOut(id=run.id, metrics={})


@eval_router.get("/runs/{run_id}")
def get_eval_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    run = db.query(models.EvalRun).filter(models.EvalRun.id == run_id).first()
    if not run:
        return {"error": "Not found"}
    require_tenant_membership(run.tenant_id, db, user, org_membership)
    return {"id": run.id, "metrics": run.metrics_json}
