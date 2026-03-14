from sqlalchemy.orm import Session

from app.db import SessionLocal, MemorySummary, UserKeypoint
from app.services.llm import summarize_turns, extract_keypoints


def summarize_session(tenant_id: str, user_id: str, session_id: str, turns: list[dict]) -> None:
    db = SessionLocal()
    try:
        summary_text = summarize_turns(turns)
        if not summary_text:
            return
        summary = MemorySummary(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            summary_text=summary_text,
            citations_json=[],
        )
        db.add(summary)
        db.commit()

        keypoints = extract_keypoints(summary_text)
        for kp in keypoints:
            db.add(
                UserKeypoint(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    keypoint_text=kp,
                    source_session_id=session_id,
                )
            )
        db.commit()
    finally:
        db.close()
