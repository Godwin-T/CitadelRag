from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    slug: str


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    org_id: str | None = None
