from __future__ import annotations

from typing import Any
from openai import OpenAI

from app.core import settings
from loguru import logger


def _llm_base_url(provider: str) -> str:
    if provider == "groq":
        return settings.groq_base_url
    if provider == "openai":
        return settings.openai_base_url
    if provider == "custom":
        return settings.custom_llm_base_url
    return settings.llm_base_url


def _embed_base_url(provider: str) -> str:
    if provider == "openai":
        return settings.openai_base_url
    if provider == "custom":
        return settings.custom_embed_base_url
    return settings.embed_base_url


def _api_key(provider: str, is_embed: bool) -> str:
    if provider == "groq":
        return settings.groq_api_key or settings.llm_api_key
    if provider == "openai":
        return settings.openai_api_key or (settings.embed_api_key if is_embed else settings.llm_api_key)
    if provider == "custom" and settings.lattice_api_key:
        return settings.lattice_api_key or (settings.embed_api_key if is_embed else settings.llm_api_key)
    return settings.embed_api_key if is_embed else settings.llm_api_key


def _client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def chat_completion(messages: list[dict[str, Any]], temperature: float = 0.2) -> str:
    provider = settings.llm_provider.lower()
    base_url = _llm_base_url(provider)
    api_key = _api_key(provider, is_embed=False)
    if not api_key:
        raise ValueError("Missing LLM API key")
    client = _client(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def embed_texts(texts: list[str]) -> list[list[float]]:
    provider = settings.embed_provider.lower()
    if provider not in {"openai", "custom"}:
        raise ValueError("Embeddings only supported for OpenAI or Lattice (custom) providers")
    base_url = _embed_base_url(provider)
    api_key = _api_key(provider, is_embed=True)
    if not api_key:
        raise ValueError("Missing Embedding API key")
    client = _client(api_key=api_key, base_url=base_url)
    logger.info(f"Api Kehy: {api_key}, Base URL: {base_url}")
    response = client.embeddings.create(model=settings.embed_model, input=texts, encoding_format="float")
    return [item.embedding for item in response.data]