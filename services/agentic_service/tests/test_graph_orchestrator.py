"""
Graph orchestrator mechanics test (interrupt/resume/checkpoint survival).

Milestone 6 note: uiux_node and coder_node now call the real UIUXAgent/
CoderAgent pipelines, which require real approved SRS/Architecture Plan
artifacts and make real LLM calls -- not appropriate for a throwaway-feature
fast test. These tests exercise the graph mechanics through the stages that
are still pass-through/auto-approved (requirement -> domain (auto) ->
architecture), which is exactly where M0 originally proved
interrupt/resume/checkpoint-survival works, and stays true for the same
reason today. The real, full run-to-completion proof (through the real
uiux_node/coder_node) is exercised manually against the real, approved
Login feature -- see CLAUDE.md for that verification.

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


def test_approve_skips_auto_approved_domain_and_reaches_architecture(feature):
    orchestrator = GraphOrchestratorService()
    orchestrator.start(feature["project_id"], feature["feature_id"])

    orchestrator.resume(feature["feature_id"], "approved")

    status = orchestrator.get_status(feature["feature_id"])
    # domain has no gate (auto-approved, Domain Agent is still a stub) -- one
    # resume from approve_requirement lands directly on approve_architecture.
    assert status["next"] == ["approve_architecture"]
    assert status["values"]["last_agent"] == "architecture"


def test_rejection_loops_back_to_same_stage(feature):
    orchestrator = GraphOrchestratorService()
    orchestrator.start(feature["project_id"], feature["feature_id"])
    orchestrator.resume(feature["feature_id"], "approved")  # -> approve_architecture

    orchestrator.resume(feature["feature_id"], "revision_requested")

    status = orchestrator.get_status(feature["feature_id"])
    # Still paused at the architecture gate, not advanced to uiux.
    assert status["next"] == ["approve_architecture"]
    assert status["values"]["last_agent"] == "architecture"


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
    first_instance.resume(feature["feature_id"], "approved")  # -> approve_architecture

    second_instance = GraphOrchestratorService()
    status_before = second_instance.get_status(feature["feature_id"])
    assert status_before["next"] == ["approve_architecture"]

    # Prove routing still works correctly post-restart (reject -> loop back).
    second_instance.resume(feature["feature_id"], "revision_requested")

    final_status = second_instance.get_status(feature["feature_id"])
    assert final_status["next"] == ["approve_architecture"]
    assert final_status["values"]["last_agent"] == "architecture"
