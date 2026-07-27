"""
Unit tests for CoderAgent._code_with_retries's control flow. No LLM, no
Docker, no git -- build_coder_react_agent/workspace_service/coder_verifier
are all mocked so this exercises pure control flow: does a GraphRecursionError
get treated as a failed attempt (committed, retried with a targeted message)
instead of crashing the whole run; does a plan-gap correctly skip the
expensive verify() call; does a passing verify() short-circuit further
attempts.
"""

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.errors import GraphRecursionError

from app.agents.coder_agent.agent import CoderAgent

CODE_PLAN = {
    "files": [
        {"path": "server/src/routes/widget.routes.js", "action": "create", "rationale": "r", "maps_to": []},
    ]
}


@pytest.fixture
def agent():
    return CoderAgent()


def _touched(paths):
    return {"added": list(paths), "modified": [], "deleted": []}


@pytest.mark.asyncio
async def test_graph_recursion_error_is_treated_as_failed_attempt_not_a_crash(agent):
    mock_react_agent = AsyncMock()
    mock_react_agent.ainvoke.side_effect = GraphRecursionError("Recursion limit of 100 reached")

    with (
        patch("app.agents.coder_agent.agent.build_coder_react_agent", return_value=mock_react_agent),
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
    ):
        mock_workspace.commit_changes.return_value = True
        mock_workspace.get_touched_files.return_value = _touched([])

        verify_result, attempts = await agent._code_with_retries("proj_x", "feature_x", CODE_PLAN)

    assert attempts == 3
    assert verify_result["passed"] is False
    assert mock_react_agent.ainvoke.call_count == 3
    # commit_changes still runs even when the loop raised -- partial progress isn't lost.
    assert mock_workspace.commit_changes.call_count == 3


@pytest.mark.asyncio
async def test_graph_recursion_error_feedback_asks_for_efficiency_on_next_attempt(agent):
    mock_react_agent = AsyncMock()
    mock_react_agent.ainvoke.side_effect = [
        GraphRecursionError("Recursion limit reached"),
        None,
    ]

    captured_messages = []

    def _fake_build_task_message(code_plan_json, prior_failure_output=None, already_touched=None):
        captured_messages.append(prior_failure_output)
        return "task message"

    with (
        patch("app.agents.coder_agent.agent.build_coder_react_agent", return_value=mock_react_agent),
        patch("app.agents.coder_agent.agent.build_task_message", side_effect=_fake_build_task_message),
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
    ):
        mock_workspace.commit_changes.return_value = True
        mock_workspace.get_touched_files.side_effect = [
            _touched([]),  # attempt 1: recursion error, nothing touched
            _touched(["server/src/routes/widget.routes.js"]),  # attempt 2: file done
        ]

        with patch.object(agent.verifier, "verify", return_value={"passed": True, "steps": []}) as mock_verify:
            verify_result, attempts = await agent._code_with_retries("proj_x", "feature_x", CODE_PLAN)

    assert attempts == 2
    assert verify_result["passed"] is True
    assert mock_verify.call_count == 1
    # Second attempt's task message must have received feedback mentioning the
    # recursion limit and asking the model to work efficiently.
    assert captured_messages[1] is not None
    assert "ran out of turns" in captured_messages[1]
    assert "work efficiently" in captured_messages[1]


@pytest.mark.asyncio
async def test_plan_gap_skips_expensive_verify_call(agent):
    mock_react_agent = AsyncMock()
    mock_react_agent.ainvoke.return_value = None

    with (
        patch("app.agents.coder_agent.agent.build_coder_react_agent", return_value=mock_react_agent),
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
    ):
        mock_workspace.commit_changes.return_value = True
        # Planned file never touched -- should trigger the gap gate, not verify().
        mock_workspace.get_touched_files.return_value = _touched([])

        with patch.object(agent.verifier, "verify") as mock_verify:
            verify_result, attempts = await agent._code_with_retries("proj_x", "feature_x", CODE_PLAN)

            assert mock_verify.call_count == 0

    assert attempts == 3
    assert verify_result["passed"] is False


@pytest.mark.asyncio
async def test_passing_verify_short_circuits_remaining_attempts(agent):
    mock_react_agent = AsyncMock()
    mock_react_agent.ainvoke.return_value = None

    with (
        patch("app.agents.coder_agent.agent.build_coder_react_agent", return_value=mock_react_agent),
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
    ):
        mock_workspace.commit_changes.return_value = True
        mock_workspace.get_touched_files.return_value = _touched(["server/src/routes/widget.routes.js"])

        with patch.object(agent.verifier, "verify", return_value={"passed": True, "steps": []}) as mock_verify:
            verify_result, attempts = await agent._code_with_retries("proj_x", "feature_x", CODE_PLAN)

    assert attempts == 1
    assert verify_result["passed"] is True
    assert mock_react_agent.ainvoke.call_count == 1
    assert mock_verify.call_count == 1
