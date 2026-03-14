from __future__ import annotations

from typing import Any
from openai import OpenAI

from api.core.config import get_settings


def _llm_base_url(provider: str, override: dict[str, str] | None = None) -> str:
    settings = get_settings()
    if override and override.get("base_url"):
        return override["base_url"]
    if provider == "groq":
        return settings.groq_base_url
    if provider == "openai":
        return settings.openai_base_url
    if provider == "custom":
        return settings.custom_llm_base_url
    return settings.llm_base_url


def _embed_base_url(provider: str, override: dict[str, str] | None = None) -> str:
    settings = get_settings()
    if override and override.get("base_url"):
        return override["base_url"]
    if provider == "openai":
        return settings.openai_base_url
    if provider == "custom":
        return settings.custom_embed_base_url
    return settings.embed_base_url


def _api_key(provider: str, is_embed: bool, override: dict[str, str] | None = None) -> str:
    settings = get_settings()
    if override and override.get("api_key"):
        return override["api_key"]
    if provider == "groq":
        return settings.groq_api_key or settings.llm_api_key
    if provider == "openai":
        return settings.openai_api_key or (settings.embed_api_key if is_embed else settings.llm_api_key)
    if provider == "custom" and settings.lattice_api_key:
        return settings.lattice_api_key or (settings.embed_api_key if is_embed else settings.llm_api_key)
    return settings.embed_api_key if is_embed else settings.llm_api_key


def _client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def chat_completion(
    messages: list[dict[str, Any]],
    temperature: float = 0.2,
    override: dict[str, str] | None = None,
    response_format: str | None = None,
) -> str:
    settings = get_settings()
    provider = (override.get("provider") if override else None) or settings.llm_provider.lower()
    model = (override.get("model") if override else None) or settings.llm_model
    base_url = _llm_base_url(provider, override=override)
    api_key = _api_key(provider, is_embed=False, override=override)
    if not api_key:
        raise ValueError("Missing LLM API key")
    client = _client(api_key=api_key, base_url=base_url)
    kwargs = {}
    if response_format == "json_object":
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs,
    )
    return response.choices[0].message.content or ""


def embed_texts(texts: list[str], override: dict[str, str] | None = None) -> list[list[float]]:
    settings = get_settings()
    provider = (override.get("provider") if override else None) or settings.embed_provider.lower()
    model = (override.get("model") if override else None) or settings.embed_model
    if provider not in {"openai", "custom"}:
        raise ValueError("Embeddings only supported for OpenAI or Lattice (custom) providers")
    base_url = _embed_base_url(provider, override=override)
    api_key = _api_key(provider, is_embed=True, override=override)
    if not api_key:
        raise ValueError("Missing Embedding API key")
    client = _client(api_key=api_key, base_url=base_url)
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]
