from pydantic import BaseModel


class SettingsOut(BaseModel):
    tenant_id: str
    llm_provider: str
    embed_provider: str
    llm_model: str | None = None
    embed_model: str | None = None
    chunk_strategy_id: str | None = None
    has_openai_key: bool = False
    has_groq_key: bool = False
    has_lattice_key: bool = False


class SettingsUpdate(BaseModel):
    tenant_id: str
    llm_provider: str | None = None
    embed_provider: str | None = None
    llm_model: str | None = None
    embed_model: str | None = None
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    lattice_api_key: str | None = None
    chunk_strategy_id: str | None = None
