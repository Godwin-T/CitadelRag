from pydantic import BaseModel


class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str


class OrganizationMe(BaseModel):
    organization: OrganizationOut
    role: str


class OrgTenantMetric(BaseModel):
    tenant_id: str
    tenant_name: str
    documents: int
    queries: int


class OrgMetrics(BaseModel):
    total_tenants: int
    total_users: int
    total_documents: int
    total_queries: int
    by_tenant: list[OrgTenantMetric]


class TenantMemberCreate(BaseModel):
    user_id: str
    role: str = "member"
