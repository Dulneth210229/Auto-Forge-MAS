"""
Unit tests for coding_loop.build_task_message's original_request parameter --
pure string-formatting, no LLM/git/Docker.
"""

from app.agents.coder_agent.coding_loop import build_task_message


def test_build_task_message_without_original_request_is_unchanged():
    message = build_task_message({"files": []})
    assert "Original human request" not in message
    assert "Implement the following pre-approved" in message


def test_build_task_message_includes_original_request_ahead_of_the_plan():
    message = build_task_message({"files": []}, original_request="Add the footer back")

    request_index = message.index("Add the footer back")
    plan_index = message.index('"files"')
    assert request_index < plan_index
    assert "Original human request" in message
    assert "trust the original request" in message


def test_build_task_message_original_request_composes_with_already_touched_and_failure():
    message = build_task_message(
        {"files": []},
        prior_failure_output="Something failed",
        already_touched={"added": ["app/page.tsx"], "modified": [], "deleted": []},
        original_request="Restore the footer",
    )

    assert "Restore the footer" in message
    assert "app/page.tsx" in message
    assert "Something failed" in message
