from api.core.config import get_settings
from api.services.llm_client import embed_texts as provider_embed_texts


def embed_texts(texts: list[str], override: dict[str, str] | None = None) -> list[list[float]]:
    try:
        return provider_embed_texts(texts, override=override)
    except Exception:
        # Fallback zero vectors if embeddings are unavailable
        settings = get_settings()
        return [[0.0] * settings.qdrant_dim for _ in texts]
