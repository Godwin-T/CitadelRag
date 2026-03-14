from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.db import models
from api.routes.deps import get_current_org_membership, get_db, require_org_admin
from api.schemas.org import OrganizationMe, OrganizationOut, OrgMetrics, OrgTenantMetric

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.get("/me", response_model=OrganizationMe)
def get_my_org(
    db: Session = Depends(get_db),
    org_membership: models.OrgMembership = Depends(get_current_org_membership),
):
    org = db.query(models.Organization).filter(models.Organization.id == org_membership.org_id).first()
    return OrganizationMe(organization=OrganizationOut(id=org.id, name=org.name, slug=org.slug), role=org_membership.role)


@router.get("/metrics", response_model=OrgMetrics)
def get_org_metrics(
    db: Session = Depends(get_db),
    org_membership: models.OrgMembership = Depends(require_org_admin),
):
    org_id = org_membership.org_id
    tenants = db.query(models.Tenant).filter(models.Tenant.org_id == org_id).all()
    tenant_ids = [t.id for t in tenants]

    total_tenants = len(tenant_ids)
    total_users = (
        db.query(func.count(models.OrgMembership.user_id))
        .filter(models.OrgMembership.org_id == org_id)
        .scalar()
        or 0
    )
    total_documents = (
        db.query(func.count(models.Document.id))
        .filter(models.Document.tenant_id.in_(tenant_ids) if tenant_ids else False)
        .scalar()
        or 0
    )
    total_queries = (
        db.query(func.count(models.Query.id))
        .filter(models.Query.tenant_id.in_(tenant_ids) if tenant_ids else False)
        .scalar()
        or 0
    )

    by_tenant: list[OrgTenantMetric] = []
    for tenant in tenants:
        doc_count = (
            db.query(func.count(models.Document.id))
            .filter(models.Document.tenant_id == tenant.id)
            .scalar()
            or 0
        )
        query_count = (
            db.query(func.count(models.Query.id))
            .filter(models.Query.tenant_id == tenant.id)
            .scalar()
            or 0
        )
        by_tenant.append(
            OrgTenantMetric(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                documents=int(doc_count),
                queries=int(query_count),
            )
        )

    return OrgMetrics(
        total_tenants=total_tenants,
        total_users=int(total_users),
        total_documents=int(total_documents),
        total_queries=int(total_queries),
        by_tenant=by_tenant,
    )
