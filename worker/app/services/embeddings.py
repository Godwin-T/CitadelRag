from app.services.llm_client import embed_texts as provider_embed_texts


MAX_TOKENS_PER_REQUEST = 250_000
CHARS_PER_TOKEN_ESTIMATE = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def batch_texts_by_tokens(texts: list[str], max_tokens: int = MAX_TOKENS_PER_REQUEST) -> list[list[str]]:
    """
    Split texts into batches that stay under the provider token-per-request limit.

    This prevents embedding calls from failing when a large document or many chunks
    push the total token count above the API's maximum request size.
    """
    batches: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0

    for text in texts:
        text_tokens = _estimate_tokens(text)
        if text_tokens > max_tokens:
            raise ValueError(f"Single text exceeds max token limit: {text_tokens} > {max_tokens}")
        if current and current_tokens + text_tokens > max_tokens:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(text)
        current_tokens += text_tokens

    if current:
        batches.append(current)

    return batches


def embed_texts(texts: list[str]) -> list[list[float]]:
    all_vectors: list[list[float]] = []
    for batch in batch_texts_by_tokens(texts):
        all_vectors.extend(provider_embed_texts(batch))
    return all_vectors
