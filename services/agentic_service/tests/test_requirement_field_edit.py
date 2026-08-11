"""
Unit tests for RequirementAgent.edit_fields -- the deterministic, no-LLM field-by-field
inline-edit backend endpoint. Reuses the same apply_revision_operations (revision_patcher.py)
the LLM-mediated /requirement/revise flow already uses; the frontend inline-edit UI is simply
another producer of the exact same operations-list shape.

Real project/feature/artifact fixtures (same convention as test_requirement_conversation.py's
conversation_fixture), no LLM/Docker -- edit_fields() makes no LLM call at all.
"""

import json
import shutil

import pytest

from app.agents.requirement_agent.agent import RequirementAgent
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id
from app.utils.slugify import slugify

VALID_SRS_JSON = {
    "project_id": "",
    "project_name": "Field Edit Test Project",
    "project_type": "E-commerce",
    "feature_id": "",
    "feature_name": "Field Edit Test Feature",
    "target_stack": "Next.js",
    "architectural_style": "modular",
    "business_goal": "Let admins manage items.",
    "scope": ["Item CRUD."],
    "out_of_scope": [],
    "user_roles": ["Admin"],
    "user_stories": [
        {"id": "US-001", "role": "Admin", "goal": "manage items", "benefit": "keep the catalog current"}
    ],
    "functional_requirements": [
        {"id": "FR-001", "description": "Admin can create an item.", "priority": "Must Have"}
    ],
    "non_functional_requirements": [
        {"id": "NFR-001", "description": "Fast.", "category": "Performance"}
    ],
    "acceptance_criteria": [
        {"id": "AC-001", "description": "Given valid input, item is created."}
    ],
    "input_requirements": [],
    "output_requirements": [],
    "ui_expectations": [],
    "api_expectations": ["POST /api/items"],
    "data_requirements": ["name (string, required)", "price (number, required)"],
    "validation_rules": [],
    "constraints": [],
    "assumptions": [],
    "risks": [],
    "dependencies": [],
    "traceability": [],
}


@pytest.fixture
def feature_with_srs(tmp_path):
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {
        "project_id": project_id,
        "project_name": "Field Edit Test Project",
        "project_type": "E-commerce",
        "target_stack": "Next.js",
    }
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": "Field Edit Test Feature",
    }

    srs_json = dict(VALID_SRS_JSON)
    srs_json["project_id"] = project_id
    srs_json["feature_id"] = feature_id

    srs_path = tmp_path / "srs_v1.json"
    srs_path.write_text(json.dumps(srs_json), encoding="utf-8")

    artifact_id = generate_id("artifact")
    store.artifacts[artifact_id] = {
        "artifact_id": artifact_id,
        "feature_id": feature_id,
        "agent_name": "requirement_agent",
        "artifact_type": "srs",
        "artifact_format": "json",
        "approval_status": "approved",
        "file_path": str(srs_path),
        "version": 1,
    }

    yield {"project_id": project_id, "feature_id": feature_id, "artifact_id": artifact_id}

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    store.database["artifacts"].delete_many({"feature_id": feature_id})

    output_root = f"outputs/{slugify('Field Edit Test Project')}/feature-{slugify('Field Edit Test Feature')}"
    shutil.rmtree(output_root, ignore_errors=True)


@pytest.fixture
def agent():
    return RequirementAgent()


def _latest_srs_json(feature_id: str) -> dict:
    matching = [
        a
        for a in store.database["artifacts"].find({"feature_id": feature_id})
        if a.get("artifact_type") == "srs" and a.get("artifact_format") == "json"
    ]
    latest = max(matching, key=lambda a: a["version"])
    return json.load(open(latest["file_path"], encoding="utf-8"))


@pytest.mark.asyncio
async def test_modify_functional_requirement_creates_a_new_version(agent, feature_with_srs):
    feature_id = feature_with_srs["feature_id"]
    operations = [
        {
            "action": "modify",
            "field": "functional_requirements",
            "target": "FR-001",
            "value": "Admin can create and edit an item.",
        }
    ]

    output = await agent.edit_fields(feature_id, operations)

    assert output.status == "revised"
    new_srs = _latest_srs_json(feature_id)
    assert new_srs["functional_requirements"][0]["description"] == "Admin can create and edit an item."
    assert new_srs["functional_requirements"][0]["id"] == "FR-001"
    assert new_srs["revision_metadata"]["revision_type"] == "manual_field_edit"
    assert new_srs["revision_metadata"]["applied_changes"]
    assert not new_srs["revision_metadata"]["unmatched_operations"]


@pytest.mark.asyncio
async def test_add_data_requirement(agent, feature_with_srs):
    feature_id = feature_with_srs["feature_id"]
    operations = [{"action": "add", "field": "data_requirements", "value": "category (string, required)"}]

    await agent.edit_fields(feature_id, operations)

    new_srs = _latest_srs_json(feature_id)
    assert "category (string, required)" in new_srs["data_requirements"]


@pytest.mark.asyncio
async def test_set_business_goal(agent, feature_with_srs):
    feature_id = feature_with_srs["feature_id"]
    operations = [{"action": "set", "field": "business_goal", "value": "Let admins fully manage the catalog."}]

    await agent.edit_fields(feature_id, operations)

    new_srs = _latest_srs_json(feature_id)
    assert new_srs["business_goal"] == "Let admins fully manage the catalog."


@pytest.mark.asyncio
async def test_unmatched_operation_is_reported_not_silently_dropped(agent, feature_with_srs):
    feature_id = feature_with_srs["feature_id"]
    operations = [
        {"action": "remove", "field": "data_requirements", "target": "this text does not exist in the SRS"}
    ]

    await agent.edit_fields(feature_id, operations)

    new_srs = _latest_srs_json(feature_id)
    assert new_srs["revision_metadata"]["unmatched_operations"]
    assert any("could not be fully applied" in a for a in new_srs["assumptions"])


@pytest.mark.asyncio
async def test_removing_the_last_functional_requirement_is_refused(agent, feature_with_srs):
    feature_id = feature_with_srs["feature_id"]
    operations = [{"action": "remove", "field": "functional_requirements", "target": "FR-001"}]

    with pytest.raises(ValueError, match="non-empty"):
        await agent.edit_fields(feature_id, operations)

    # No new version was saved -- the SRS is still exactly v1, unchanged.
    matching = [
        a for a in store.database["artifacts"].find({"feature_id": feature_id})
        if a.get("artifact_type") == "srs" and a.get("artifact_format") == "json"
    ]
    assert len(matching) == 1


@pytest.mark.asyncio
async def test_stale_base_artifact_id_is_rejected(agent, feature_with_srs):
    feature_id = feature_with_srs["feature_id"]
    operations = [{"action": "set", "field": "business_goal", "value": "Something else."}]

    with pytest.raises(ValueError, match="updated by another change"):
        await agent.edit_fields(feature_id, operations, base_artifact_id="artifact_does_not_exist")


@pytest.mark.asyncio
async def test_matching_base_artifact_id_is_accepted(agent, feature_with_srs):
    feature_id = feature_with_srs["feature_id"]
    artifact_id = feature_with_srs["artifact_id"]
    operations = [{"action": "set", "field": "business_goal", "value": "Something else."}]

    output = await agent.edit_fields(feature_id, operations, base_artifact_id=artifact_id)

    assert output.status == "revised"


@pytest.mark.asyncio
async def test_no_prior_srs_raises(agent):
    project_id = generate_id("project")
    feature_id = generate_id("feature")
    store.projects[project_id] = {"project_id": project_id, "project_name": "No SRS Project"}
    store.features[feature_id] = {"project_id": project_id, "feature_id": feature_id, "feature_name": "No SRS"}

    with pytest.raises(ValueError, match="No existing SRS"):
        await agent.edit_fields(feature_id, [{"action": "set", "field": "business_goal", "value": "x"}])

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
