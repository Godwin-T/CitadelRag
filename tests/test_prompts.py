from api.prompts.prompts import (
    SYSTEM_SUMMARIZER,
    build_llm_chunk_messages,
    build_rag_messages,
    build_summary_messages,
)


def test_build_rag_messages_shape():
    messages = build_rag_messages("memory", "question", ["source"])
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_summary_messages_uses_system_prompt():
    messages = build_summary_messages([{"role": "user", "content": "hi"}])
    assert messages[0]["content"] == SYSTEM_SUMMARIZER


def test_build_llm_chunk_messages_shape():
    messages = build_llm_chunk_messages("text", 100, 10)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
