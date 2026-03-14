from functools import lru_cache
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CitadelRAG API"
    environment: str = "development"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://citadel:citadel@localhost:5432/citadel"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    jwt_secret: str = "dev-secret"
    jwt_issuer: str = "citadelrag"
    jwt_exp_minutes: int = 60 * 24
    password_reset_ttl_minutes: int = 60 * 24
    password_reset_base_url: str = "http://localhost:5174/reset-password"

    llm_base_url: str = "http://localhost:8001/v1"
    llm_model: str = "openai/gpt-oss-20b"
    embed_base_url: str = "http://localhost:8002/v1"
    embed_model: str = "text-embedding-ada-002"

    llm_provider: str = "groq"
    embed_provider: str = "openai"
    llm_api_key: str = ""
    embed_api_key: str = ""
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    custom_llm_base_url: str = ""
    custom_embed_base_url: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    hf_embed_base_url: str = ""
    lattice_api_key: str = ""

    upload_dir: str = "./storage/uploads"
    memory_ttl_seconds: int = 60 * 60 * 24

    summary_interval_turns: int = 8
    summary_max_tokens: int = 512
    small_talk_bypass: bool = True

    qdrant_collection: str = "citadel_chunks"
    qdrant_dim: int = 1536
    auto_migrate: bool = False
    log_level: str = "INFO"
    log_json: bool = False
    log_file: str = ""

    storage_backend: str = "s3"
    s3_endpoint: str = "http://minio:9000"
    s3_bucket: str = "citadel-docs"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    local_upload_dir: str = "./storage/uploads"


class TokenData(BaseModel):
    user_id: str
    tenant_id: str | None = None
    org_id: str | None = None
    org_role: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
