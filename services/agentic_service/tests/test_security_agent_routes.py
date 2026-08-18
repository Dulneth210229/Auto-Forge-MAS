"""
Unit tests for POST /features/{feature_id}/agents/security/run -- the first API route this
agent has ever had (previously zero, unlike every other agent's /run + /revise[/stream] set).
Real TestClient (established convention, see test_database_connection_routes.py);
security_agent.run() itself is mocked (its own real-scan behavior is already covered by
test_security_agent.py and the scanner unit tests) -- this file only exercises the route's own
wiring: 404 on an unknown feature, the AgentRunResponse shape, and error translation.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.security_agent.schemas import SecurityAgentOutput
from app.main import app
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id

client = TestClient(app)


@pytest.fixture
def feature_id():
    project_id = generate_id("project")
    fid = generate_id("feature")
    store.projects[project_id] = {"project_id": project_id, "project_name": "Security Route Test"}
    store.features[fid] = {
        "feature_id": fid,
        "project_id": project_id,
        "feature_name": "Security Route Test Feature",
    }

    yield fid

    store.database["features"].delete_one({"feature_id": fid})
    store.database["projects"].delete_one({"project_id": project_id})


def test_run_returns_404_for_unknown_feature():
    response = client.post(
        "/api/v1/features/feature_does_not_exist/agents/security/run", json={}
    )
    assert response.status_code == 404


def test_run_returns_agent_run_response_shape(feature_id):
    fake_output = SecurityAgentOutput(
        status="completed",
        gate_decision="review",
        findings_count=3,
        critical_count=0,
        moderate_count=2,
        warning_count=1,
        artifact_ids=["artifact_json", "artifact_md"],
        message="3 finding(s), gate=review.",
    )

    with patch(
        "app.api.routes.agents.security_agent.run", new=AsyncMock(return_value=fake_output)
    ):
        response = client.post(
            f"/api/v1/features/{feature_id}/agents/security/run", json={}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["feature_id"] == feature_id
    assert body["agent_name"] == "security_agent"
    assert body["status"] == "completed"
    assert body["artifact_ids"] == ["artifact_json", "artifact_md"]
    assert "3 finding" in body["message"]


def test_run_accepts_optional_human_comment(feature_id):
    fake_output = SecurityAgentOutput(status="completed", artifact_ids=[], message="0 finding(s), gate=pass.")

    with patch(
        "app.api.routes.agents.security_agent.run", new=AsyncMock(return_value=fake_output)
    ):
        response = client.post(
            f"/api/v1/features/{feature_id}/agents/security/run",
            json={"human_comment": "Re-scan after the fix."},
        )

    assert response.status_code == 200


def test_run_translates_unexpected_exception_to_500(feature_id):
    with patch(
        "app.api.routes.agents.security_agent.run",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        response = client.post(
            f"/api/v1/features/{feature_id}/agents/security/run", json={}
        )

    assert response.status_code == 500
    assert "Security Agent failed" in response.json()["detail"]
