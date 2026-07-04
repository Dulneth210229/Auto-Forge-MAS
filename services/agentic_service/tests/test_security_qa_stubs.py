"""
Unit tests for the Security/QA Agent placeholders and their graph node
wiring. No LLM involved -- both agents are still stubs that return
immediately without touching the workspace.
"""

import asyncio

from app.agents.qa_agent.agent import qa_agent
from app.agents.security_agent.agent import security_agent
from app.services.graph_orchestrator_service import _qa_node, _security_node


def test_security_agent_stub_returns_skipped():
    result = asyncio.run(security_agent.run(feature_id="fake_feature"))
    assert result == {"status": "skipped", "message": "Security Agent not yet implemented."}


def test_qa_agent_stub_returns_skipped():
    result = asyncio.run(qa_agent.run(feature_id="fake_feature"))
    assert result == {"status": "skipped", "message": "QA Agent not yet implemented."}


def test_security_node_advances_state_without_gating():
    state = {"feature_id": "fake_feature", "human_comment": "some prior comment"}

    result = _security_node(state)

    assert result == {
        "last_agent": "security",
        "last_artifact_ids": [],
        "human_comment": None,
    }


def test_qa_node_advances_state_without_gating():
    state = {"feature_id": "fake_feature", "human_comment": "some prior comment"}

    result = _qa_node(state)

    assert result == {
        "last_agent": "qa",
        "last_artifact_ids": [],
        "human_comment": None,
    }
