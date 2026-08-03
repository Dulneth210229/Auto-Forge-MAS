"""
Unit tests for approval_service.submit_approval's SRS exclusivity rule: approving one SRS
version supersedes (reverts to pending) any OTHER SRS version already approved for the same
feature, so at most one SRS version is ever "approved" at a time. Real Mongo-backed `store`
seeding (established test convention, e.g. test_artifact_active_selection.py), no LLM/graph.
"""

import json

import pytest

from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.schemas.approval_schema import ApprovalRequest
from app.services.approval_service import approval_service
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id


def _seed_artifact(tmp_path, project_id, feature_id, *, artifact_type, version, approval_status):
    artifact_id = generate_id("artifact")
    file_path = tmp_path / f"{artifact_id}.json"
    file_path.write_text(json.dumps({"version": version}), encoding="utf-8")

    store.artifacts[artifact_id] = {
        "artifact_id": artifact_id,
        "project_id": project_id,
        "feature_id": feature_id,
        "agent_name": AgentName.REQUIREMENT.value,
        "artifact_type": artifact_type,
        "artifact_format": ArtifactFormat.JSON.value,
        "approval_status": approval_status,
        "file_path": str(file_path),
        "version": version,
    }
    return artifact_id


@pytest.fixture
def feature_with_one_approved_srs(tmp_path):
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {
        "project_id": project_id,
        "project_name": "Exclusivity Test Project",
        "project_type": "E-commerce",
        "target_stack": "MERN",
    }
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": "Exclusivity Test Feature",
        "feature_description": "test feature",
    }

    v1_id = _seed_artifact(
        tmp_path, project_id, feature_id, artifact_type=ArtifactType.SRS.value, version=1,
        approval_status=ApprovalStatus.APPROVED.value,
    )
    v2_id = _seed_artifact(
        tmp_path, project_id, feature_id, artifact_type=ArtifactType.SRS.value, version=2,
        approval_status=ApprovalStatus.PENDING.value,
    )

    yield {"project_id": project_id, "feature_id": feature_id, "v1_id": v1_id, "v2_id": v2_id}

    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    store.database["artifacts"].delete_many({"feature_id": feature_id})
    store.database["approvals"].delete_many({"feature_id": feature_id})


def test_approving_a_new_srs_version_supersedes_the_previously_approved_one(feature_with_one_approved_srs):
    v1_id = feature_with_one_approved_srs["v1_id"]
    v2_id = feature_with_one_approved_srs["v2_id"]

    approval_service.submit_approval(v2_id, ApprovalRequest(status=ApprovalStatus.APPROVED))

    assert store.artifacts.get(v2_id)["approval_status"] == ApprovalStatus.APPROVED.value
    assert store.artifacts.get(v1_id)["approval_status"] == ApprovalStatus.PENDING.value


def test_rejecting_or_requesting_revision_does_not_touch_other_versions(feature_with_one_approved_srs):
    v1_id = feature_with_one_approved_srs["v1_id"]
    v2_id = feature_with_one_approved_srs["v2_id"]

    approval_service.submit_approval(v2_id, ApprovalRequest(status=ApprovalStatus.REJECTED))

    assert store.artifacts.get(v2_id)["approval_status"] == ApprovalStatus.REJECTED.value
    # v1 stays approved -- only an actual APPROVAL of a sibling version supersedes it.
    assert store.artifacts.get(v1_id)["approval_status"] == ApprovalStatus.APPROVED.value


def test_exclusivity_does_not_affect_other_artifact_types(feature_with_one_approved_srs, tmp_path):
    feature_id = feature_with_one_approved_srs["feature_id"]
    project_id = feature_with_one_approved_srs["project_id"]
    v2_id = feature_with_one_approved_srs["v2_id"]

    component_a = _seed_artifact(
        tmp_path, project_id, feature_id, artifact_type=ArtifactType.UI_COMPONENT_CODE.value, version=1,
        approval_status=ApprovalStatus.APPROVED.value,
    )
    component_b = _seed_artifact(
        tmp_path, project_id, feature_id, artifact_type=ArtifactType.UI_COMPONENT_CODE.value, version=1,
        approval_status=ApprovalStatus.APPROVED.value,
    )

    approval_service.submit_approval(v2_id, ApprovalRequest(status=ApprovalStatus.APPROVED))

    # Two independently-approved UI components of the same type must both stay approved -- the
    # SRS exclusivity rule must never bleed into unrelated artifact_types.
    assert store.artifacts.get(component_a)["approval_status"] == ApprovalStatus.APPROVED.value
    assert store.artifacts.get(component_b)["approval_status"] == ApprovalStatus.APPROVED.value

    store.database["artifacts"].delete_many({"artifact_id": {"$in": [component_a, component_b]}})
