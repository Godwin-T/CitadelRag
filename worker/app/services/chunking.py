from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from app.services.embeddings import embed_texts
from app.services.llm import llm_chunk_text


@dataclass
class ChunkResult:
    text: str
    metadata: dict[str, Any]


Chunker = Callable[[str, dict[str, Any]], list[ChunkResult]]


DEFAULT_PARAMS = {
    "max_chars": 1000,
    "overlap": 100,
}


def chunk_text(text: str, strategy_name: str, params: dict[str, Any] | None = None) -> list[ChunkResult]:
    params = params or {}
    chunker = CHUNKER_REGISTRY.get(strategy_name, fixed_chunker)
    return chunker(text, params)


def fixed_chunker(text: str, params: dict[str, Any]) -> list[ChunkResult]:
    max_chars = int(params.get("max_chars", DEFAULT_PARAMS["max_chars"]))
    overlap = int(params.get("overlap", DEFAULT_PARAMS["overlap"]))
    chunks = _fixed_split(text, max_chars=max_chars, overlap=overlap)
    return [ChunkResult(text=c, metadata={}) for c in chunks]


def recursive_chunker(text: str, params: dict[str, Any]) -> list[ChunkResult]:
    max_chars = int(params.get("max_chars", DEFAULT_PARAMS["max_chars"]))
    overlap = int(params.get("overlap", DEFAULT_PARAMS["overlap"]))
    separators = params.get("separators") or ["\n\n", "\n", ". ", " "]
    splits = _recursive_split(text, separators, max_chars)
    merged = _merge_splits(splits, max_chars)
    merged = _apply_overlap(merged, overlap)
    return [ChunkResult(text=c, metadata={}) for c in merged]


def sentence_chunker(text: str, params: dict[str, Any]) -> list[ChunkResult]:
    max_chars = int(params.get("max_chars", DEFAULT_PARAMS["max_chars"]))
    overlap = int(params.get("overlap", DEFAULT_PARAMS["overlap"]))
    min_sentence_chars = int(params.get("min_sentence_chars", 20))
    sentences = _split_sentences(text)
    sentences = [s for s in sentences if len(s.strip()) >= min_sentence_chars]
    chunks = _pack_units(sentences, max_chars)
    chunks = _apply_overlap(chunks, overlap)
    return [ChunkResult(text=c, metadata={}) for c in chunks]


def paragraph_chunker(text: str, params: dict[str, Any]) -> list[ChunkResult]:
    max_chars = int(params.get("max_chars", 1200))
    overlap = int(params.get("overlap", DEFAULT_PARAMS["overlap"]))
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    chunks = _pack_units(paragraphs, max_chars)
    chunks = _apply_overlap(chunks, overlap)
    return [ChunkResult(text=c, metadata={}) for c in chunks]


def header_chunker(text: str, params: dict[str, Any]) -> list[ChunkResult]:
    max_chars = int(params.get("max_chars", 1500))
    overlap = int(params.get("overlap", DEFAULT_PARAMS["overlap"]))
    header_regex = params.get("header_regex") or r"^#{1,6}\s+.+$"
    header_pattern = re.compile(header_regex)

    sections: list[tuple[str, str]] = []
    current_header = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        if header_pattern.match(line.strip()):
            if current_lines:
                sections.append((current_header, "\n".join(current_lines)))
            current_header = line.strip()
            current_lines = [line.strip()]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_header, "\n".join(current_lines)))

    if not sections:
        return fixed_chunker(text, params)

    results: list[ChunkResult] = []
    for header, content in sections:
        if len(content) <= max_chars:
            results.append(ChunkResult(text=content.strip(), metadata={"header_path": header}))
        else:
            split_chunks = _fixed_split(content, max_chars=max_chars, overlap=overlap)
            for chunk in split_chunks:
                results.append(ChunkResult(text=chunk, metadata={"header_path": header}))
    return results


def semantic_chunker(text: str, params: dict[str, Any]) -> list[ChunkResult]:
    max_chars = int(params.get("max_chars", 1200))
    overlap = int(params.get("overlap", DEFAULT_PARAMS["overlap"]))
    similarity_threshold = float(params.get("similarity_threshold", 0.75))
    max_sentences = int(params.get("max_sentences", 10))

    sentences = _split_sentences(text)
    if not sentences:
        return fixed_chunker(text, params)

    embeddings = embed_texts(sentences)
    chunks: list[str] = []
    current: list[str] = []
    for idx, sentence in enumerate(sentences):
        if not current:
            current.append(sentence)
            continue
        if len(current) >= max_sentences:
            chunks.append(" ".join(current).strip())
            current = [sentence]
            continue
        prev_vec = embeddings[idx - 1]
        curr_vec = embeddings[idx]
        sim = _cosine_similarity(prev_vec, curr_vec)
        candidate = " ".join(current + [sentence])
        if sim < similarity_threshold or len(candidate) > max_chars:
            chunks.append(" ".join(current).strip())
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        chunks.append(" ".join(current).strip())

    chunks = _apply_overlap(chunks, overlap)
    return [ChunkResult(text=c, metadata={}) for c in chunks]


def llm_chunker(text: str, params: dict[str, Any]) -> list[ChunkResult]:
    max_chars = int(params.get("max_chars", 1200))
    overlap = int(params.get("overlap", DEFAULT_PARAMS["overlap"]))
    llm_format = params.get("llm_format", "json_list")

    chunks = llm_chunk_text(text=text, max_chars=max_chars, overlap=overlap, llm_format=llm_format)
    if not chunks:
        return fixed_chunker(text, params)
    return [ChunkResult(text=c, metadata={}) for c in chunks]


CHUNKER_REGISTRY: dict[str, Chunker] = {
    "fixed": fixed_chunker,
    "default": fixed_chunker,
    "recursive": recursive_chunker,
    "sentence": sentence_chunker,
    "paragraph": paragraph_chunker,
    "header": header_chunker,
    "semantic": semantic_chunker,
    "llm": llm_chunker,
}


def _fixed_split(text: str, max_chars: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end].strip())
        start = end - overlap
        if start < 0:
            start = 0
        if end == len(text):
            break
    return [c for c in chunks if c]


def _recursive_split(text: str, separators: list[str], max_chars: int) -> list[str]:
    if len(text) <= max_chars or not separators:
        return [text]
    sep = separators[0]
    if sep:
        parts = text.split(sep)
        parts = [p + sep for p in parts[:-1]] + [parts[-1]]
    else:
        parts = list(text)
    splits: list[str] = []
    for part in parts:
        if len(part) > max_chars and len(separators) > 1:
            splits.extend(_recursive_split(part, separators[1:], max_chars))
        else:
            splits.append(part)
    return splits


def _merge_splits(parts: list[str], max_chars: int) -> list[str]:
    merged: list[str] = []
    current = ""
    for part in parts:
        if len(current) + len(part) <= max_chars:
            current += part
        else:
            if current:
                merged.append(current.strip())
            current = part
    if current:
        merged.append(current.strip())
    return [m for m in merged if m]


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    if overlap <= 0:
        return chunks
    overlapped = [chunks[0]] if chunks else []
    for idx in range(1, len(chunks)):
        prefix = chunks[idx - 1][-overlap:]
        overlapped.append((prefix + chunks[idx]).strip())
    return overlapped


def _pack_units(units: list[str], max_chars: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for unit in units:
        unit = unit.strip()
        if not unit:
            continue
        unit_len = len(unit)
        # If a single unit is larger than max_chars, flush current and add unit as its own chunk.
        if unit_len > max_chars:
            if current:
                chunks.append(" ".join(current).strip())
                current = []
                current_len = 0
            chunks.append(unit)
            continue

        # Account for space between units when packing.
        additional = unit_len + (1 if current else 0)
        if current_len + additional <= max_chars:
            current.append(unit)
            current_len += additional
        else:
            if current:
                chunks.append(" ".join(current).strip())
            current = [unit]
            current_len = unit_len

    if current:
        chunks.append(" ".join(current).strip())

    return [c for c in chunks if c]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a)
    vb = np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
