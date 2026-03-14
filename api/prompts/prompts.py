from __future__ import annotations

from typing import Any

SYSTEM_RAG_INSTRUCTIONS = "You are a RAG system. Use the sources to answer. Include citations by chunk_id."
SYSTEM_CITATION_ASSISTANT = "You are a citation-focused assistant."
SYSTEM_FAITHFULNESS_SCORER = "Score faithfulness from 0 to 100."
SYSTEM_SUMMARIZER = "Summarize the conversation succinctly."
SYSTEM_KEYPOINT_EXTRACTOR = "Extract user keypoints as bullet list."
SYSTEM_LLM_CHUNKER = (
    "You are a chunking assistant. Return a JSON list of chunk strings. "
    "Do not include any commentary or extra text."
)
SYSTEM_HIGHLIGHT_QA = "You answer questions using only the highlighted passage."
SYSTEM_SMALL_TALK_DECIDER = """
You are a classifier. Decide if the user's message is a greeting, pleasantry, or a simple question that can be answered directly without document retrieval.
- If the message is a greeting, pleasantry, or a simple direct question (e.g., "How are you?", "What's the capital of France?"), set "small_talk" to true and provide a direct, friendly response (e.g., "Hello! How can I assist you today?").
- If it’s not small talk (e.g., complex queries requiring document retrieval), set "small_talk" to false and leave the "response" empty.

Examples:
1. User: "Hi!"
   Response: {{"small_talk": true, "response": "Hello! How can I help?"}}
2. User: "How are you?"
   Response: {{"small_talk": true, "response": "I'm doing well, thanks! How can I assist you?"}}
3. User: "What's the capital of France?"
   Response: {{"small_talk": true, "response": "The capital of France is Paris."}}
4. User: "Can you explain machine learning?"
   Response: {{"small_talk": false, "response": ""}}

Return only json object

```json
{"small_talk": boolean, "response": string}
"""


def build_rag_messages(memory_context: str, question: str, sources: list[str]) -> list[dict[str, Any]]:
    system_content = f"{SYSTEM_CITATION_ASSISTANT} {SYSTEM_RAG_INSTRUCTIONS}"
    user_content = (
        f"Memory Context:\n{memory_context}\n\n"
        f"Question: {question}\n"
        f"Sources:\n{sources}"
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def build_faithfulness_messages(answer: str, sources: list[str]) -> list[dict[str, Any]]:
    user_content = f"Answer: {answer}\nSources: {sources}"
    return [
        {"role": "system", "content": SYSTEM_FAITHFULNESS_SCORER},
        {"role": "user", "content": user_content},
    ]


def build_summary_messages(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    content = "\n".join([f"{t.get('role')}: {t.get('content')}" for t in turns])
    return [
        {"role": "system", "content": SYSTEM_SUMMARIZER},
        {"role": "user", "content": content},
    ]


def build_keypoint_messages(summary: str) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": SYSTEM_KEYPOINT_EXTRACTOR},
        {"role": "user", "content": summary},
    ]


def build_llm_chunk_messages(text: str, max_chars: int, overlap: int, llm_format: str = "json_list") -> list[dict[str, Any]]:
    user_content = (
        f"Chunk the following text. Max chars per chunk: {max_chars}. "
        f"Overlap: {overlap}. Format: {llm_format}.\\n\\n{text}"
    )
    return [
        {"role": "system", "content": SYSTEM_LLM_CHUNKER},
        {"role": "user", "content": user_content},
    ]


def build_highlight_messages(
    highlight_text: str, question: str, sources: list[str] | None = None
) -> list[dict[str, Any]]:
    source_block = "\n".join(sources or [])
    user_content = (
        f"Highlight:\n{highlight_text}\n\n"
        f"Question: {question}\n"
        f"Sources:\n{source_block}"
    )
    return [
        {"role": "system", "content": SYSTEM_HIGHLIGHT_QA},
        {"role": "user", "content": user_content},
    ]
