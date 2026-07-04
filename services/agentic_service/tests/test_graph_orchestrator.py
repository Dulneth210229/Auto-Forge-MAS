"""
Milestone 0 isolation test: the top-level LangGraph orchestrator.

This exercises the graph mechanics only (interrupt/resume/checkpoint survival)
using pass-through nodes -- no LLM calls, no real agent logic. Real agent
integration is tested separately as each agent is rebuilt.

Requires a reachable MongoDB (the same one configured in .env / MONGODB_URI).
Every project/feature this test creates is deleted in a fixture teardown, and
the collections it writes checkpoints into are LangGraph-owned
(langgraph_checkpoints / langgraph_checkpoint_writes), never the app's own
projects/features/artifacts collections.
"""

import pytest

from app.services.graph_orchestrator_service import (
    GraphNotRunningError,
    GraphOrchestratorService,
)
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id


@pytest.fixture
def feature():
    """
    Create a throwaway project + feature in the real store, and clean up
    (including its LangGraph checkpoint documents) after the test.
    """
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {
        "project_id": project_id,
        "project_name": f"Test Project {project_id}",
    }
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": f"Test Feature {feature_id}",
    }

    yield {"project_id": project_id, "feature_id": feature_id}

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    store.database["langgraph_checkpoints"].delete_many({"thread_id": feature_id})
    store.database["langgraph_checkpoint_writes"].delete_many({"thread_id": feature_id})


def test_start_pauses_at_first_approval_gate(feature):
    orchestrator = GraphOrchestratorService()

    result = orchestrator.start(feature["project_id"], feature["feature_id"])

    assert "__interrupt__" in result
    status = orchestrator.get_status(feature["feature_id"])
    assert status["next"] == ["approve_requirement"]


def test_approve_advances_to_next_stage(feature):
    orchestrator = GraphOrchestratorService()
    orchestrator.start(feature["project_id"], feature["feature_id"])

    orchestrator.resume(feature["feature_id"], "approved")

    status = orchestrator.get_status(feature["feature_id"])
    assert status["next"] == ["approve_domain"]
    assert status["values"]["last_agent"] == "domain"


def test_rejection_loops_back_to_same_stage(feature):
    orchestrator = GraphOrchestratorService()
    orchestrator.start(feature["project_id"], feature["feature_id"])
    orchestrator.resume(feature["feature_id"], "approved")  # -> domain

    orchestrator.resume(feature["feature_id"], "revision_requested")

    status = orchestrator.get_status(feature["feature_id"])
    # Still paused at the domain gate, not advanced to architecture.
    assert status["next"] == ["approve_domain"]
    assert status["values"]["last_agent"] == "domain"


def test_full_run_reaches_completion(feature):
    orchestrator = GraphOrchestratorService()
    orchestrator.start(feature["project_id"], feature["feature_id"])

    # requirement -> domain -> architecture -> uiux -> coder
    for _ in range(5):
        orchestrator.resume(feature["feature_id"], "approved")

    status = orchestrator.get_status(feature["feature_id"])

    # security/qa are auto-approved pass-through stages: no gate to resume.
    assert status["next"] == []
    assert status["values"]["last_agent"] == "qa"


def test_resume_without_a_paused_run_raises(feature):
    orchestrator = GraphOrchestratorService()
    # Never started -- there is no paused run for this feature_id.
    with pytest.raises(GraphNotRunningError):
        orchestrator.resume(feature["feature_id"], "approved")


def test_resume_survives_a_fresh_orchestrator_instance(feature):
    """
    Simulates a backend restart: a brand-new GraphOrchestratorService (fresh
    graph build, fresh checkpointer handle) must be able to resume a run
    started by a different instance, reading state from MongoDB only.
    """
    first_instance = GraphOrchestratorService()
    first_instance.start(feature["project_id"], feature["feature_id"])
    first_instance.resume(feature["feature_id"], "approved")  # -> domain

    second_instance = GraphOrchestratorService()
    status_before = second_instance.get_status(feature["feature_id"])
    assert status_before["next"] == ["approve_domain"]

    for _ in range(4):
        second_instance.resume(feature["feature_id"], "approved")

    final_status = second_instance.get_status(feature["feature_id"])
    assert final_status["next"] == []
    assert final_status["values"]["last_agent"] == "qa"
