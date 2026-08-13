"""
Unit tests for approval_service.submit_approval's UI/UX Preview Screenshot cascade: approving,
rejecting, or requesting revision on a ui_preview_screenshot artifact must apply the exact same
decision to ui_metadata (JSON+Markdown), ui_integration_manifest, every ui_component_code, every
ui_page_html, AND any other ui_preview_screenshot of the SAME version -- per direct user request,
only the Preview Screenshot is independently approvable for the uiux stage; everything else
cascades from it. Mirrors test_approval_architecture_cascade.py's exact structure. Also covers the
new cross-version exclusivity rule for UI_PREVIEW_SCREENSHOT and its interaction with the cascade.

Real Mongo-backed `store` seeding (established convention), no LLM/graph.
"""

import json

import pytest

from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.schemas.approval_schema import ApprovalRequest
from app.services.approval_service import approval_service
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id


def _seed_artifact(
    tmp_path, project_id, feature_id, *, artifact_type, artifact_format, version, approval_status,
    agent_name=AgentName.UIUX.value,
):
    artifact_id = generate_id("artifact")
    file_path = tmp_path / f"{artifact_id}.dat"
    file_path.write_text(json.dumps({"version": version}), encoding="utf-8")

    store.artifacts[artifact_id] = {
        "artifact_id": artifact_id,
        "project_id": project_id,
        "feature_id": feature_id,
        "agent_name": agent_name,
        "artifact_type": artifact_type,
        "artifact_format": artifact_format,
        "approval_status": approval_status,
        "file_path": str(file_path),
        "version": version,
    }
    return artifact_id


def _seed_full_uiux_generation(tmp_path, project_id, feature_id, version, approval_status, page_count=1):
    """Seeds the real artifact rows one UI/UX Agent run produces for a single version: metadata
    JSON+Markdown, integration manifest, 2 components, and page_count pages each with a page-html
    + preview-screenshot pair."""
    ids = {}
    ids["metadata_json"] = _seed_artifact(
        tmp_path, project_id, feature_id, artifact_type=ArtifactType.UI_METADATA.value,
        artifact_format=ArtifactFormat.JSON.value, version=version, approval_status=approval_status,
    )
    ids["metadata_markdown"] = _seed_artifact(
        tmp_path, project_id, feature_id, artifact_type=ArtifactType.UI_METADATA.value,
        artifact_format=ArtifactFormat.MARKDOWN.value, version=version, approval_status=approval_status,
    )
    ids["manifest"] = _seed_artifact(
        tmp_path, project_id, feature_id, artifact_type=ArtifactType.UI_INTEGRATION_MANIFEST.value,
        artifact_format=ArtifactFormat.JSON.value, version=version, approval_status=ApprovalStatus.PENDING.value,
    )
    for name in ("item_list", "item_details"):
        ids[f"component_{name}"] = _seed_artifact(
            tmp_path, project_id, feature_id, artifact_type=ArtifactType.UI_COMPONENT_CODE.value,
            artifact_format=ArtifactFormat.HTML.value, version=version, approval_status=ApprovalStatus.PENDING.value,
        )
    ids["screenshots"] = []
    ids["page_htmls"] = []
    for index in range(page_count):
        page_html_id = _seed_artifact(
            tmp_path, project_id, feature_id, artifact_type=ArtifactType.UI_PAGE_HTML.value,
            artifact_format=ArtifactFormat.HTML.value, version=version, approval_status=ApprovalStatus.PENDING.value,
        )
        screenshot_id = _seed_artifact(
            tmp_path, project_id, feature_id, artifact_type=ArtifactType.UI_PREVIEW_SCREENSHOT.value,
            artifact_format=ArtifactFormat.PNG.value, version=version, approval_status=ApprovalStatus.PENDING.value,
        )
        ids["page_htmls"].append(page_html_id)
        ids["screenshots"].append(screenshot_id)
    ids["screenshot"] = ids["screenshots"][0]
    ids["page_html"] = ids["page_htmls"][0]
    return ids


@pytest.fixture
def feature_with_one_uiux_generation(tmp_path):
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {
        "project_id": project_id, "project_name": "UIUX Cascade Test Project",
        "project_type": "E-commerce", "target_stack": "Next.js",
    }
    store.features[feature_id] = {
        "project_id": project_id, "feature_id": feature_id,
        "feature_name": "UIUX Cascade Test Feature", "feature_description": "test feature",
    }

    ids = _seed_full_uiux_generation(tmp_path, project_id, feature_id, version=1, approval_status=ApprovalStatus.PENDING.value)

    yield {"project_id": project_id, "feature_id": feature_id, **ids}

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    store.database["artifacts"].delete_many({"feature_id": feature_id})
    store.database["approvals"].delete_many({"feature_id": feature_id})


def test_approving_screenshot_cascades_to_metadata_manifest_components_and_page_html(feature_with_one_uiux_generation):
    ids = feature_with_one_uiux_generation

    approval_service.submit_approval(ids["screenshot"], ApprovalRequest(status=ApprovalStatus.APPROVED))

    assert store.artifacts.get(ids["screenshot"])["approval_status"] == ApprovalStatus.APPROVED.value
    assert store.artifacts.get(ids["metadata_json"])["approval_status"] == ApprovalStatus.APPROVED.value
    assert store.artifacts.get(ids["metadata_markdown"])["approval_status"] == ApprovalStatus.APPROVED.value
    assert store.artifacts.get(ids["manifest"])["approval_status"] == ApprovalStatus.APPROVED.value
    assert store.artifacts.get(ids["component_item_list"])["approval_status"] == ApprovalStatus.APPROVED.value
    assert store.artifacts.get(ids["component_item_details"])["approval_status"] == ApprovalStatus.APPROVED.value
    assert store.artifacts.get(ids["page_html"])["approval_status"] == ApprovalStatus.APPROVED.value


@pytest.mark.parametrize("status", [ApprovalStatus.REJECTED, ApprovalStatus.REVISION_REQUESTED])
def test_reject_and_revision_requested_cascade_the_same_way(feature_with_one_uiux_generation, status):
    ids = feature_with_one_uiux_generation

    approval_service.submit_approval(ids["screenshot"], ApprovalRequest(status=status))

    assert store.artifacts.get(ids["screenshot"])["approval_status"] == status.value
    assert store.artifacts.get(ids["metadata_json"])["approval_status"] == status.value
    assert store.artifacts.get(ids["manifest"])["approval_status"] == status.value
    assert store.artifacts.get(ids["component_item_list"])["approval_status"] == status.value
    assert store.artifacts.get(ids["page_html"])["approval_status"] == status.value


def test_approving_one_screenshot_cascades_to_a_different_pages_screenshot_same_version(tmp_path):
    """A two-page feature has two ui_preview_screenshot artifacts of the same version -- approving
    one must cascade to the OTHER screenshot too (not just the non-screenshot siblings), since a
    human clicking Approve on the representative screenshot is meant as one decision for the whole
    version."""
    project_id = generate_id("project")
    feature_id = generate_id("feature")
    store.projects[project_id] = {"project_id": project_id, "project_name": "P", "project_type": "E-commerce", "target_stack": "Next.js"}
    store.features[feature_id] = {"project_id": project_id, "feature_id": feature_id, "feature_name": "F", "feature_description": "d"}

    try:
        ids = _seed_full_uiux_generation(tmp_path, project_id, feature_id, version=1, approval_status=ApprovalStatus.PENDING.value, page_count=2)

        approval_service.submit_approval(ids["screenshots"][0], ApprovalRequest(status=ApprovalStatus.APPROVED))

        assert store.artifacts.get(ids["screenshots"][0])["approval_status"] == ApprovalStatus.APPROVED.value
        assert store.artifacts.get(ids["screenshots"][1])["approval_status"] == ApprovalStatus.APPROVED.value
        assert store.artifacts.get(ids["page_htmls"][1])["approval_status"] == ApprovalStatus.APPROVED.value
    finally:
        store.database["projects"].delete_one({"project_id": project_id})
        store.database["features"].delete_one({"feature_id": feature_id})
        store.database["artifacts"].delete_many({"feature_id": feature_id})
        store.database["approvals"].delete_many({"feature_id": feature_id})


def test_cascade_never_touches_a_different_version(tmp_path):
    project_id = generate_id("project")
    feature_id = generate_id("feature")
    store.projects[project_id] = {"project_id": project_id, "project_name": "P", "project_type": "E-commerce", "target_stack": "Next.js"}
    store.features[feature_id] = {"project_id": project_id, "feature_id": feature_id, "feature_name": "F", "feature_description": "d"}

    try:
        v1 = _seed_full_uiux_generation(tmp_path, project_id, feature_id, version=1, approval_status=ApprovalStatus.PENDING.value)
        v2 = _seed_full_uiux_generation(tmp_path, project_id, feature_id, version=2, approval_status=ApprovalStatus.PENDING.value)

        approval_service.submit_approval(v2["screenshot"], ApprovalRequest(status=ApprovalStatus.APPROVED))

        assert store.artifacts.get(v2["screenshot"])["approval_status"] == ApprovalStatus.APPROVED.value
        assert store.artifacts.get(v2["metadata_json"])["approval_status"] == ApprovalStatus.APPROVED.value
        # v1's rows (a different version) are completely untouched by v2's cascade.
        assert store.artifacts.get(v1["screenshot"])["approval_status"] == ApprovalStatus.PENDING.value
        assert store.artifacts.get(v1["metadata_json"])["approval_status"] == ApprovalStatus.PENDING.value
        assert store.artifacts.get(v1["component_item_list"])["approval_status"] == ApprovalStatus.PENDING.value
    finally:
        store.database["projects"].delete_one({"project_id": project_id})
        store.database["features"].delete_one({"feature_id": feature_id})
        store.database["artifacts"].delete_many({"feature_id": feature_id})
        store.database["approvals"].delete_many({"feature_id": feature_id})


def test_cascaded_siblings_get_an_honest_synthetic_approval_record(feature_with_one_uiux_generation):
    ids = feature_with_one_uiux_generation

    approval_service.submit_approval(ids["screenshot"], ApprovalRequest(status=ApprovalStatus.APPROVED, approved_by="human_user"))

    metadata_approvals = [a for a in store.approvals.values() if a["artifact_id"] == ids["metadata_json"]]
    assert len(metadata_approvals) == 1
    assert metadata_approvals[0]["approved_by"] == "system:uiux_screenshot_cascade"
    assert "not an independent human decision" in metadata_approvals[0]["reviewer_comment"]

    # The screenshot's OWN approval record is a real, human-attributed one -- the cascade must
    # never overwrite or duplicate it.
    screenshot_approvals = [a for a in store.approvals.values() if a["artifact_id"] == ids["screenshot"]]
    assert len(screenshot_approvals) == 1
    assert screenshot_approvals[0]["approved_by"] == "human_user"


def test_approving_a_new_screenshot_version_reverts_the_old_version_and_its_cascade(tmp_path):
    """New cross-version exclusivity rule for UI_PREVIEW_SCREENSHOT (mirrors ARCHITECTURE_PLAN):
    only one screenshot version is ever "the approved one". Superseding an old, already-approved-
    and-cascaded version must revert that old version's own metadata/components/page-html too, or
    they go out of sync."""
    project_id = generate_id("project")
    feature_id = generate_id("feature")
    store.projects[project_id] = {"project_id": project_id, "project_name": "P", "project_type": "E-commerce", "target_stack": "Next.js"}
    store.features[feature_id] = {"project_id": project_id, "feature_id": feature_id, "feature_name": "F", "feature_description": "d"}

    try:
        v1 = _seed_full_uiux_generation(tmp_path, project_id, feature_id, version=1, approval_status=ApprovalStatus.PENDING.value)
        # v1 already approved (and cascaded) in an earlier, real approval action.
        approval_service.submit_approval(v1["screenshot"], ApprovalRequest(status=ApprovalStatus.APPROVED))
        assert store.artifacts.get(v1["metadata_json"])["approval_status"] == ApprovalStatus.APPROVED.value

        v2 = _seed_full_uiux_generation(tmp_path, project_id, feature_id, version=2, approval_status=ApprovalStatus.PENDING.value)
        approval_service.submit_approval(v2["screenshot"], ApprovalRequest(status=ApprovalStatus.APPROVED))

        # v2 (and its cascade) are now the approved ones.
        assert store.artifacts.get(v2["screenshot"])["approval_status"] == ApprovalStatus.APPROVED.value
        assert store.artifacts.get(v2["metadata_json"])["approval_status"] == ApprovalStatus.APPROVED.value

        # v1's screenshot reverted to pending (new exclusivity rule) AND v1's own cascade reverted
        # too -- the real risk this test locks in.
        assert store.artifacts.get(v1["screenshot"])["approval_status"] == ApprovalStatus.PENDING.value
        assert store.artifacts.get(v1["metadata_json"])["approval_status"] == ApprovalStatus.PENDING.value
        assert store.artifacts.get(v1["metadata_markdown"])["approval_status"] == ApprovalStatus.PENDING.value
        assert store.artifacts.get(v1["component_item_list"])["approval_status"] == ApprovalStatus.PENDING.value
        assert store.artifacts.get(v1["page_html"])["approval_status"] == ApprovalStatus.PENDING.value
    finally:
        store.database["projects"].delete_one({"project_id": project_id})
        store.database["features"].delete_one({"feature_id": feature_id})
        store.database["artifacts"].delete_many({"feature_id": feature_id})
        store.database["approvals"].delete_many({"feature_id": feature_id})


def test_cascade_never_bleeds_into_unrelated_artifact_types(feature_with_one_uiux_generation, tmp_path):
    ids = feature_with_one_uiux_generation
    project_id = ids["project_id"]
    feature_id = ids["feature_id"]

    unrelated = _seed_artifact(
        tmp_path, project_id, feature_id, artifact_type=ArtifactType.ARCHITECTURE_PLAN.value,
        artifact_format=ArtifactFormat.JSON.value, version=1, approval_status=ApprovalStatus.PENDING.value,
        agent_name=AgentName.ARCHITECTURE.value,
    )

    approval_service.submit_approval(ids["screenshot"], ApprovalRequest(status=ApprovalStatus.APPROVED))

    assert store.artifacts.get(unrelated)["approval_status"] == ApprovalStatus.PENDING.value

    store.database["artifacts"].delete_one({"artifact_id": unrelated})


def test_apply_design_system_patch_triggers_on_screenshot_approval(feature_with_one_uiux_generation, monkeypatch):
    """apply_design_system_patch's trigger was widened to fire on UI_PREVIEW_SCREENSHOT approval
    (not just the old, no-longer-directly-approved UI_METADATA) -- confirms the real call fires,
    without needing a real design_system.json/project_memory_service round trip."""
    ids = feature_with_one_uiux_generation
    calls = []

    from app.agents.uiux_agent import agent as uiux_agent_module

    def fake_apply_design_system_patch(self, feature_id, version):
        calls.append((feature_id, version))

    monkeypatch.setattr(uiux_agent_module.UIUXAgent, "apply_design_system_patch", fake_apply_design_system_patch)

    approval_service.submit_approval(ids["screenshot"], ApprovalRequest(status=ApprovalStatus.APPROVED))

    assert calls == [(ids["feature_id"], 1)]
