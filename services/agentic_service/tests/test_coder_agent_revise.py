"""
Unit tests for CoderAgent.revise()'s control flow -- the new capability
letting a human iterate on an existing Coder Agent run by prompt, the same
way Requirement/Architecture Agent's .revise() already work. No LLM, no
Docker, no git: the planner, coding loop, and verifier are all mocked; only
`store` (real Mongo-backed, matching this repo's established test
convention for feature/project/artifact seeding) is real.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.coder_agent.agent import CoderAgent
from app.agents.coder_agent.planner import CodePlanGenerationError
from app.core.enums import AgentName, ArtifactFormat, ArtifactType
from app.schemas.coder_schema import CoderAgentReviseRequest
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id

EXISTING_PLAN = {
    "files": [
        {"path": "server/src/routes/widget.routes.js", "action": "create", "rationale": "r", "maps_to": []}
    ],
    "new_dependencies": [],
    "env_vars_needed": [],
    "summary": "s",
}


def _seed_artifact(feature_id: str, agent_name: str, artifact_type: str, file_path, version: int = 1) -> str:
    artifact_id = generate_id("artifact")
    store.artifacts[artifact_id] = {
        "artifact_id": artifact_id,
        "feature_id": feature_id,
        "agent_name": agent_name,
        "artifact_type": artifact_type,
        "artifact_format": ArtifactFormat.JSON.value,
        "approval_status": "approved",
        "file_path": str(file_path),
        "version": version,
    }
    return artifact_id


@pytest.fixture
def feature_with_prior_run(tmp_path):
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {"project_id": project_id, "project_name": "Revise Test Project"}
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": "Revise Test Feature",
    }

    srs_path = tmp_path / "srs.json"
    srs_path.write_text('{"functional_requirements": []}', encoding="utf-8")
    _seed_artifact(feature_id, AgentName.REQUIREMENT.value, ArtifactType.SRS.value, srs_path)

    arch_path = tmp_path / "arch.json"
    arch_path.write_text('{"design_views": {}}', encoding="utf-8")
    _seed_artifact(feature_id, AgentName.ARCHITECTURE.value, ArtifactType.ARCHITECTURE_PLAN.value, arch_path)

    plan_path = tmp_path / "code_plan_v1.json"
    plan_path.write_text(json.dumps(EXISTING_PLAN), encoding="utf-8")
    _seed_artifact(feature_id, AgentName.CODER.value, ArtifactType.CODE_PLAN.value, plan_path)

    yield {"project_id": project_id, "feature_id": feature_id}

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    store.database["artifacts"].delete_many({"feature_id": feature_id})


ARCHITECTURE_PLAN_WITH_COVERAGE = {
    "design_views": {
        "interface_view": {"api_endpoints": [{"endpoint": "/api/task-comments"}]},
        "data_view": {"data_entities": [{"name": "Comment"}]},
    }
}

PRIOR_PLAN_COVERING_EVERYTHING = {
    "files": [
        {
            "path": "server/src/routes/task-comments.routes.js",
            "action": "create",
            "rationale": "r",
            "maps_to": ["/api/task-comments", "Comment"],
        },
        {
            "path": "client/src/components/CommentList.jsx",
            "action": "create",
            "rationale": "r",
            "maps_to": [],
        },
    ],
    "new_dependencies": [],
    "env_vars_needed": [],
    "summary": "s",
}


@pytest.fixture
def feature_with_two_prior_revisions(tmp_path):
    """
    Reproduces a real bug found only after a *second* revise() call against
    a live feature: v1 is the original, full plan (covers every endpoint/
    entity); v2 is a prior revision's own saved plan, which -- correctly,
    by design -- only lists the delta that revision touched. If coverage
    were checked against only the *latest* version's files, a third
    revision would lose everything v1 covers, since v2 alone doesn't
    restate it.
    """
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {"project_id": project_id, "project_name": "Two Revisions Project"}
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": "Two Revisions Feature",
    }

    srs_path = tmp_path / "srs.json"
    srs_path.write_text('{"functional_requirements": []}', encoding="utf-8")
    _seed_artifact(feature_id, AgentName.REQUIREMENT.value, ArtifactType.SRS.value, srs_path)

    arch_path = tmp_path / "arch.json"
    arch_path.write_text(json.dumps(ARCHITECTURE_PLAN_WITH_COVERAGE), encoding="utf-8")
    _seed_artifact(feature_id, AgentName.ARCHITECTURE.value, ArtifactType.ARCHITECTURE_PLAN.value, arch_path)

    v1_path = tmp_path / "code_plan_v1.json"
    v1_path.write_text(json.dumps(PRIOR_PLAN_COVERING_EVERYTHING), encoding="utf-8")
    _seed_artifact(feature_id, AgentName.CODER.value, ArtifactType.CODE_PLAN.value, v1_path, version=1)

    v2_delta_plan = {
        "files": [
            {
                "path": "client/src/components/CommentList.jsx",
                "action": "modify",
                "rationale": "A prior revision's own delta.",
                "maps_to": [],
            }
        ],
        "new_dependencies": [],
        "env_vars_needed": [],
        "summary": "A prior revision.",
    }
    v2_path = tmp_path / "code_plan_v2.json"
    v2_path.write_text(json.dumps(v2_delta_plan), encoding="utf-8")
    _seed_artifact(feature_id, AgentName.CODER.value, ArtifactType.CODE_PLAN.value, v2_path, version=2)

    yield {"project_id": project_id, "feature_id": feature_id}

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    store.database["artifacts"].delete_many({"feature_id": feature_id})


@pytest.fixture
def feature_with_full_coverage_prior_run(tmp_path):
    """
    Prior plan that fully covers a real architecture plan's endpoints/
    entities -- for testing that a revision's own (necessarily partial) new
    plan doesn't get rejected for "missing" things the prior plan, still in
    place, already implements.
    """
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {"project_id": project_id, "project_name": "Coverage Revise Project"}
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": "Coverage Revise Feature",
    }

    srs_path = tmp_path / "srs.json"
    srs_path.write_text('{"functional_requirements": []}', encoding="utf-8")
    _seed_artifact(feature_id, AgentName.REQUIREMENT.value, ArtifactType.SRS.value, srs_path)

    arch_path = tmp_path / "arch.json"
    arch_path.write_text(json.dumps(ARCHITECTURE_PLAN_WITH_COVERAGE), encoding="utf-8")
    _seed_artifact(feature_id, AgentName.ARCHITECTURE.value, ArtifactType.ARCHITECTURE_PLAN.value, arch_path)

    plan_path = tmp_path / "code_plan_v1.json"
    plan_path.write_text(json.dumps(PRIOR_PLAN_COVERING_EVERYTHING), encoding="utf-8")
    _seed_artifact(feature_id, AgentName.CODER.value, ArtifactType.CODE_PLAN.value, plan_path)

    yield {"project_id": project_id, "feature_id": feature_id}

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    store.database["artifacts"].delete_many({"feature_id": feature_id})


@pytest.fixture
def feature_with_no_prior_run():
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {"project_id": project_id, "project_name": "No Prior Run Project"}
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": "No Prior Run Feature",
    }

    yield {"project_id": project_id, "feature_id": feature_id}

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})


@pytest.fixture
def agent():
    return CoderAgent()


@pytest.mark.asyncio
async def test_revise_raises_when_no_prior_code_plan_exists(agent, feature_with_no_prior_run):
    request = CoderAgentReviseRequest(revision_comment="Add a loading spinner.")

    with pytest.raises(ValueError, match="No existing Coder Agent output"):
        await agent.revise(feature_with_no_prior_run["feature_id"], request)


@pytest.mark.asyncio
async def test_revise_resumes_existing_branch_not_start_fresh(agent, feature_with_prior_run):
    project_id = feature_with_prior_run["project_id"]
    feature_id = feature_with_prior_run["feature_id"]
    request = CoderAgentReviseRequest(revision_comment="Add a loading spinner.")

    with (
        patch.object(agent.planner, "generate_via_exploration", new=AsyncMock(return_value=(EXISTING_PLAN, "raw"))),
        patch.object(agent.plan_validator, "validate", return_value=None),
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
        patch.object(
            agent, "_code_with_retries", new=AsyncMock(return_value=({"passed": True, "steps": []}, 1))
        ),
        patch.object(agent, "_save_artifacts", return_value=["artifact_new"]),
    ):
        mock_workspace.diff_against_main.return_value = {
            "added": [], "modified": [], "deleted": [], "diff_text": ""
        }

        output = await agent.revise(feature_id, request)

    mock_workspace.resume_feature_branch.assert_called_once_with(project_id, feature_id)
    mock_workspace.start_feature_branch.assert_not_called()
    assert output.verification_passed is True
    assert output.artifact_ids == ["artifact_new"]


@pytest.mark.asyncio
async def test_revise_resumes_the_branch_before_planning_not_after(agent, feature_with_prior_run):
    """
    Required ordering for the agentic revision planner: its read-only tools
    (list_dir/read_file/search_code) read whatever is currently checked out
    in the workspace, so the feature branch must already be checked out
    before planning starts -- not after, which is how run()'s
    start_feature_branch/planning order works (there, planning happens
    before any branch exists at all).
    """
    feature_id = feature_with_prior_run["feature_id"]
    request = CoderAgentReviseRequest(revision_comment="Add a loading spinner.")

    call_order = []

    async def _fake_generate_via_exploration(**kwargs):
        call_order.append("generate_via_exploration")
        return EXISTING_PLAN, "raw"

    with (
        patch.object(agent.planner, "generate_via_exploration", new=_fake_generate_via_exploration),
        patch.object(agent.plan_validator, "validate", return_value=None),
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
        patch.object(
            agent, "_code_with_retries", new=AsyncMock(return_value=({"passed": True, "steps": []}, 1))
        ),
        patch.object(agent, "_save_artifacts", return_value=["artifact_new"]),
    ):
        mock_workspace.diff_against_main.return_value = {
            "added": [], "modified": [], "deleted": [], "diff_text": ""
        }
        mock_workspace.resume_feature_branch.side_effect = lambda *a, **k: call_order.append(
            "resume_feature_branch"
        )

        await agent.revise(feature_id, request)

    assert call_order == ["resume_feature_branch", "generate_via_exploration"]


@pytest.mark.asyncio
async def test_revise_frames_the_existing_plan_as_a_revision_not_a_rejection(agent, feature_with_prior_run):
    feature_id = feature_with_prior_run["feature_id"]
    request = CoderAgentReviseRequest(revision_comment="Add a loading spinner while comments load.")

    captured = {}

    async def _fake_generate_via_exploration(**kwargs):
        captured["previous_plan_json"] = kwargs.get("previous_plan_json")
        captured["validation_feedback"] = kwargs.get("validation_feedback")
        captured["human_comment"] = kwargs.get("human_comment")
        return EXISTING_PLAN, "raw"

    with (
        patch.object(agent.planner, "generate_via_exploration", new=_fake_generate_via_exploration),
        patch.object(agent.plan_validator, "validate", return_value=None),
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
        patch.object(
            agent, "_code_with_retries", new=AsyncMock(return_value=({"passed": True, "steps": []}, 1))
        ),
        patch.object(agent, "_save_artifacts", return_value=["artifact_new"]),
    ):
        mock_workspace.diff_against_main.return_value = {
            "added": [], "modified": [], "deleted": [], "diff_text": ""
        }

        await agent.revise(feature_id, request)

    assert captured["previous_plan_json"] == EXISTING_PLAN
    assert captured["human_comment"] == request.revision_comment
    # Must NOT claim the existing (already-good) plan was rejected -- that
    # would be false and would confuse the model about what to change.
    assert "REJECTED" not in captured["validation_feedback"]
    assert "HUMAN-REQUESTED REVISION" in captured["validation_feedback"]


@pytest.mark.asyncio
async def test_revise_validates_coverage_against_prior_plan_union_not_delta_alone(
    agent, feature_with_full_coverage_prior_run
):
    """
    Reproduces a real bug found running revise() end-to-end against a live
    feature: the model's new plan for a small, targeted revision (e.g. "add
    a loading spinner") only lists the file(s) that change, not every
    endpoint/entity the *prior* plan already covers -- and the real
    plan_validator (not mocked here) rejected that as incomplete coverage,
    even though the prior plan (still in place, untouched by this revision)
    already implements everything else. Coverage must be checked against the
    union of the prior plan's files and this delta, not the delta alone.
    """
    project_id = feature_with_full_coverage_prior_run["project_id"]
    feature_id = feature_with_full_coverage_prior_run["feature_id"]
    request = CoderAgentReviseRequest(revision_comment="Add a loading spinner while comments load.")

    delta_only_plan = {
        "files": [
            {
                "path": "client/src/components/CommentList.jsx",
                "action": "modify",
                "rationale": "Add loading spinner",
                "maps_to": [],
            }
        ],
        "new_dependencies": [],
        "env_vars_needed": [],
        "summary": "Add a loading state to CommentList.",
    }

    with (
        patch.object(agent.planner, "generate_via_exploration", new=AsyncMock(return_value=(delta_only_plan, "raw"))),
        # plan_validator is intentionally NOT mocked here -- the real coverage
        # check is exactly what this test is verifying.
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
        patch.object(
            agent, "_code_with_retries", new=AsyncMock(return_value=({"passed": True, "steps": []}, 1))
        ),
        patch.object(agent, "_save_artifacts", return_value=["artifact_new"]),
    ):
        mock_workspace.diff_against_main.return_value = {
            "added": [], "modified": [], "deleted": [], "diff_text": ""
        }

        output = await agent.revise(feature_id, request)

    # The delta plan actually coded is still just the delta, not a merged plan.
    assert output.code_plan_json == delta_only_plan
    assert output.verification_passed is True


@pytest.mark.asyncio
async def test_revise_coverage_baseline_spans_every_prior_version_not_just_the_latest(
    agent, feature_with_two_prior_revisions
):
    """
    Reproduces a real bug found running a SECOND revise() against a live
    feature: v1 (the original plan) covers everything; v2 (a prior
    revision's own saved plan) only lists its own delta, by design. A THIRD
    revision's coverage baseline, if built from only the *latest* saved
    plan (v2), would lose everything v1 covers -- exactly the false
    "does not cover these API endpoints" rejection a real user hit through
    the /coder/revise endpoint. The baseline must span every version ever
    saved for this feature, not just the most recent one.
    """
    project_id = feature_with_two_prior_revisions["project_id"]
    feature_id = feature_with_two_prior_revisions["feature_id"]
    request = CoderAgentReviseRequest(revision_comment="Now also add a delete confirmation dialog.")

    third_delta_plan = {
        "files": [
            {
                "path": "client/src/components/CommentList.jsx",
                "action": "modify",
                "rationale": "Add delete confirmation dialog",
                "maps_to": [],
            }
        ],
        "new_dependencies": [],
        "env_vars_needed": [],
        "summary": "Add a confirmation dialog before deleting a comment.",
    }

    with (
        patch.object(agent.planner, "generate_via_exploration", new=AsyncMock(return_value=(third_delta_plan, "raw"))),
        # plan_validator is intentionally NOT mocked here -- the real coverage
        # check is exactly what this test is verifying.
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
        patch.object(
            agent, "_code_with_retries", new=AsyncMock(return_value=({"passed": True, "steps": []}, 1))
        ),
        patch.object(agent, "_save_artifacts", return_value=["artifact_new"]),
    ):
        mock_workspace.diff_against_main.return_value = {
            "added": [], "modified": [], "deleted": [], "diff_text": ""
        }

        output = await agent.revise(feature_id, request)

    assert output.code_plan_json == third_delta_plan
    assert output.verification_passed is True


@pytest.mark.asyncio
async def test_revise_retries_exploration_planning_after_it_runs_out_of_turns(
    agent, feature_with_full_coverage_prior_run
):
    """
    Reproduces a real bug found running a genuinely vague revision request
    ("styles are missing, add tailwind css") against a live feature: the
    agentic exploration planner used 16 real tool-calling turns and still
    hadn't called submit_code_plan when its turn budget ran out, raising
    CodePlanGenerationError uncaught -- crashing the whole revise() call
    instead of being treated as a recoverable attempt, the same way
    _code_with_retries already treats a GraphRecursionError from the coding
    loop. This confirms the fix: a CodePlanGenerationError from the
    exploration path is now caught and retried with an efficiency-focused
    hint, not left to crash the request.
    """
    feature_id = feature_with_full_coverage_prior_run["feature_id"]
    request = CoderAgentReviseRequest(revision_comment="Styles are missing, add tailwind css.")

    delta_plan = {
        "files": [
            {
                "path": "client/src/components/CommentList.jsx",
                "action": "modify",
                "rationale": "Add tailwind styling",
                "maps_to": [],
            }
        ],
        "new_dependencies": [],
        "env_vars_needed": [],
        "summary": "Add tailwind styling.",
    }

    captured_feedback = []

    async def _fake_generate_via_exploration(**kwargs):
        captured_feedback.append(kwargs.get("validation_feedback"))
        if len(captured_feedback) == 1:
            raise CodePlanGenerationError(
                "Coder Agent's agentic revision planner ended without calling "
                "submit_code_plan (either it stopped early or hit the exploration turn limit of 50)."
            )
        return delta_plan, "raw"

    with (
        patch.object(agent.planner, "generate_via_exploration", new=_fake_generate_via_exploration),
        # plan_validator is intentionally NOT mocked -- confirms the real coverage
        # union check still passes for the eventual successful attempt.
        patch("app.agents.coder_agent.agent.workspace_service") as mock_workspace,
        patch.object(
            agent, "_code_with_retries", new=AsyncMock(return_value=({"passed": True, "steps": []}, 1))
        ),
        patch.object(agent, "_save_artifacts", return_value=["artifact_new"]),
    ):
        mock_workspace.diff_against_main.return_value = {
            "added": [], "modified": [], "deleted": [], "diff_text": ""
        }

        output = await agent.revise(feature_id, request)

    assert len(captured_feedback) == 2
    assert "HUMAN-REQUESTED REVISION" in captured_feedback[0]  # first attempt: normal revision framing
    assert "summarizing tool" in captured_feedback[1]  # second attempt: strategy-change hint fed back
    assert output.code_plan_json == delta_plan
    assert output.verification_passed is True
