from typing import Any

from api.prompts.prompts import build_faithfulness_messages, SYSTEM_SMALL_TALK_DECIDER
from api.schemas.query import SmallTalkDecision
from api.services.llm_validation import parse_llm_json
from api.services.llm_client import chat_completion
from loguru import logger


def generate_answer(
    messages: list[dict[str, Any]],
    citations: list[dict[str, Any]] | None = None,
    override: dict[str, str] | None = None,
) -> str:
    try:
        return chat_completion(messages, temperature=0.2, override=override)
    except Exception:
        return "No answer available."


def score_faithfulness(answer: str, sources: list[str], override: dict[str, str] | None = None) -> int:
    messages = build_faithfulness_messages(answer, sources)
    try:
        text = chat_completion(messages, temperature=0.0, override=override)
        score = int("".join(ch for ch in text if ch.isdigit()) or "0")
        return max(0, min(score, 100))
    except Exception:
        return 0


def small_talk_decision(message: str, override: dict[str, str] | None = None) -> dict[str, str | bool]:
    messages = [
        {"role": "system", "content": SYSTEM_SMALL_TALK_DECIDER},
        {"role": "user", "content": message},
    ]
    last_error: Exception | None = None
    for _ in range(2):
        try:
            raw = chat_completion(messages, temperature=0.0, override=override, response_format="json_object")
            parsed = parse_llm_json(raw, SmallTalkDecision)
            logger.info(f"Small-talk decision: {parsed.small_talk}, response: {parsed.response}")
            return {"small_talk": parsed.small_talk, "response": parsed.response}
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("Small-talk decision validation failed after retry") from last_error
