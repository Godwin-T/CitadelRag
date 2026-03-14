import json
from api.prompts.prompts import build_keypoint_messages, build_llm_chunk_messages, build_summary_messages
from app.services.llm_client import chat_completion


def summarize_turns(turns: list[dict]) -> str:
    messages = build_summary_messages(turns)
    try:
        return chat_completion(messages, temperature=0.2)
    except Exception:
        return ""


def extract_keypoints(summary: str) -> list[str]:
    if not summary:
        return []
    messages = build_keypoint_messages(summary)
    try:
        text = chat_completion(messages, temperature=0.0)
        return [line.strip("- ") for line in text.splitlines() if line.strip()]
    except Exception:
        return []


def llm_chunk_text(text: str, max_chars: int, overlap: int, llm_format: str = "json_list") -> list[str]:
    messages = build_llm_chunk_messages(text=text, max_chars=max_chars, overlap=overlap, llm_format=llm_format)
    try:
        raw = chat_completion(messages, temperature=0.0)
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "chunks" in parsed:
            parsed = parsed["chunks"]
        if not isinstance(parsed, list):
            return []
        return [str(c).strip() for c in parsed if str(c).strip()]
    except Exception:
        return []
