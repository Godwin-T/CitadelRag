from api.prompts.prompts import build_summary_messages


def test_worker_imports_prompts():
    messages = build_summary_messages([])
    assert isinstance(messages, list)
