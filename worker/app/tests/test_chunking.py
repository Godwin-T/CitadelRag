import re

from app.services import chunking


def test_fixed_chunker_default():
    text = "A" * 2100
    results = chunking.chunk_text(text, "fixed", {"max_chars": 1000, "overlap": 100})
    assert len(results) >= 2
    assert all(r.text for r in results)


def test_recursive_chunker_splits_large_text():
    text = "para1\n\npara2\n\npara3"
    results = chunking.chunk_text(text, "recursive", {"max_chars": 10})
    assert len(results) >= 2


def test_sentence_chunker_respects_sentence_boundaries():
    text = "First sentence. Second sentence! Third sentence?"
    results = chunking.chunk_text(text, "sentence", {"max_chars": 30, "overlap": 0})
    assert all(r.text.endswith(('.', '!', '?')) for r in results if r.text)


def test_paragraph_chunker_respects_blank_lines():
    text = "Para1\n\nPara2\n\nPara3"
    results = chunking.chunk_text(text, "paragraph", {"max_chars": 20, "overlap": 0})
    assert len(results) == 3


def test_header_chunker_splits_by_headers():
    text = "# Intro\nA\n# Details\nB"
    results = chunking.chunk_text(text, "header", {"max_chars": 100})
    assert len(results) == 2
    assert results[0].metadata.get("header_path") == "# Intro"


def test_semantic_chunker_threshold(monkeypatch):
    text = "One. Two. Three. Four."

    def fake_embed(texts):
        vectors = []
        for i in range(len(texts)):
            vectors.append([1.0, 0.0] if i % 2 == 0 else [0.0, 1.0])
        return vectors

    monkeypatch.setattr(chunking, "embed_texts", fake_embed)
    results = chunking.chunk_text(text, "semantic", {"similarity_threshold": 0.9, "max_chars": 100})
    assert len(results) >= 2


def test_llm_chunker_parses_json(monkeypatch):
    def fake_llm_chunk_text(text, max_chars, overlap, llm_format):
        return ["chunk1", "chunk2"]

    monkeypatch.setattr(chunking, "llm_chunk_text", fake_llm_chunk_text)
    results = chunking.chunk_text("text", "llm", {"max_chars": 10})
    assert [r.text for r in results] == ["chunk1", "chunk2"]
