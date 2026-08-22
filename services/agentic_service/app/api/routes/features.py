"""
Feature routes.

A feature is one SDLC unit.

Example:
- Login
- Signup
- Product Listing

When a feature is created, the artifact folder structure is also created.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Response
from pydantic import ValidationError

from app.core.enums import FeatureStatus, AgentName
from app.schemas.approval_schema import ApprovalResponse
from app.schemas.feature_schema import FeatureCreateRequest, FeatureResponse, SetActiveArtifactSelectionRequest
from app.schemas.stage_event_schema import StageEventResponse
from app.services.approval_service import approval_service
from app.services.artifact_service import artifact_service
from app.services.graph_orchestrator_service import graph_orchestrator_service
from app.services.in_memory_store import store
from app.services.stage_event_service import stage_event_service
from app.services.workspace_service import workspace_service
from app.utils.id_generator import generate_id
from app.utils.logger import get_logger
from app.utils.slugify import slugify

logger = get_logger(__name__)

router = APIRouter(tags=["Features"])


@router.post("/projects/{project_id}/features", response_model=FeatureResponse)
def create_feature(project_id: str, request: FeatureCreateRequest):
    """
    Create a feature inside a project.

    This also creates the required artifact folders.
    """
    project = store.projects.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.utcnow()
    feature_id = generate_id("feature")

    feature = {
        "feature_id": feature_id,
        "project_id": project_id,
        "feature_name": request.feature_name,
        "feature_description": request.feature_description,
        "feature_status": FeatureStatus.CREATED,
        "current_agent": AgentName.REQUIREMENT,
        "created_at": now,
        "updated_at": now,
    }

    store.features[feature_id] = feature

    # Create artifact folder structure immediately.
    artifact_service.create_feature_artifact_root(
        project_name=project["project_name"],
        feature_name=feature["feature_name"]
    )

    return FeatureResponse(**feature)


@router.get("/projects/{project_id}/features", response_model=list[FeatureResponse])
def list_project_features(project_id: str):
    """
    Return all features for a project.

    Skips (and logs a warning for) any individual record that fails to validate -- a
    malformed/legacy feature document should not break this list for every other, valid
    feature in the same project.
    """
    project = store.projects.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    results = []

    for feature in store.features.values():
        if feature["project_id"] != project_id:
            continue

        try:
            results.append(FeatureResponse(**feature))
        except ValidationError as error:
            logger.warning("Skipping unparseable feature %s: %s", feature.get("feature_id"), error)

    return results


@router.get("/features/{feature_id}", response_model=FeatureResponse)
def get_feature(feature_id: str):
    """
    Return one feature by ID.
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return FeatureResponse(**feature)


@router.put("/features/{feature_id}/artifacts/active-selection", response_model=FeatureResponse)
def set_active_artifact_selection(feature_id: str, request: SetActiveArtifactSelectionRequest):
    """
    Pin which APPROVED version of one artifact_type should feed the next pipeline stage for this
    feature -- e.g. which approved SRS version the Domain Agent reads, when more than one SRS
    version has been approved and the latest one isn't the one a human wants to proceed with.
    Only an approved artifact of the given type can be selected (400 otherwise).
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    try:
        artifact_service.set_active_artifact_selection(
            feature_id=feature_id,
            artifact_type=request.artifact_type,
            artifact_id=request.artifact_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return FeatureResponse(**store.features.get(feature_id))


@router.delete("/features/{feature_id}", status_code=204)
def delete_feature(feature_id: str):
    """
    Permanently delete one feature: its artifacts, approvals, stage events, and requirement
    conversation record. Scoped to this feature only -- unlike delete_project, never touches the
    project's knowledge documents or the whole workspace repo (other features in the same project
    may still need those). Best-effort discards this feature's own git branch, but ONLY if the
    project's workspace repo already exists on disk with a real branch for this feature -- never
    creates a workspace as a side effect of deleting a feature that never advanced far enough to
    have one (ensure_project_repo, which discard_feature_branch calls internally, would otherwise
    do exactly that).
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    project_id = feature["project_id"]
    artifact_ids = [a["artifact_id"] for a in store.artifacts.values() if a.get("feature_id") == feature_id]

    store.artifacts.collection.delete_many({"feature_id": feature_id})
    store.approvals.collection.delete_many(
        {"$or": [{"feature_id": feature_id}, {"artifact_id": {"$in": artifact_ids}}]}
    )
    store.stage_events.collection.delete_many({"feature_id": feature_id})
    store.requirement_conversations.collection.delete_one({"feature_id": feature_id})
    store.qa_conversations.collection.delete_one({"feature_id": feature_id})

    repo_path = workspace_service.get_repo_path(project_id)
    if (repo_path / ".git").exists():
        try:
            workspace_service.discard_feature_branch(project_id, feature_id)
        except Exception as error:
            logger.warning("Failed to discard git branch for deleted feature_id=%s: %s", feature_id, error)

    store.features.collection.delete_one({"feature_id": feature_id})


@router.post("/features/{feature_id}/start")
def start_feature_pipeline(feature_id: str):
    """
    Start this feature's LangGraph pipeline run.

    This kicks off the graph for the first time; every step after that is
    driven by approval decisions hitting POST /artifacts/{artifact_id}/approval,
    which resume the same paused run (see graph_orchestrator_service).
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    graph_orchestrator_service.start(
        project_id=feature["project_id"],
        feature_id=feature_id,
    )

    return graph_orchestrator_service.get_status(feature_id)


@router.get("/features/{feature_id}/graph-status")
def get_feature_graph_status(feature_id: str):
    """
    Return this feature's current LangGraph pipeline state: {"next": [...], "values": {...}}.

    Previously this shape was only ever returned once, inline, as POST /start's response
    body -- this route exposes the same, already-existing graph_orchestrator_service.get_status
    lookup so the frontend can poll it at any time (e.g. to detect Domain/UI-UX/Coder Agent
    auto-completing after a prior stage's approval). Before /start has ever been called for a
    feature, this returns an idle snapshot ("next": [] and empty "values") -- not an error.
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return graph_orchestrator_service.get_status(feature_id)


@router.get("/features/{feature_id}/approvals", response_model=list[ApprovalResponse])
def list_feature_approvals(feature_id: str):
    """
    Return every approval decision recorded for this feature, oldest first.

    Powers the frontend's per-stage activity timeline -- a real record of every
    approve/reject/revision-request decision and its reviewer_comment, not previously
    retrievable at all (only POST /artifacts/{id}/approval existed before this).
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return approval_service.list_feature_approvals(feature_id)


@router.get("/features/{feature_id}/events", response_model=list[StageEventResponse])
def list_feature_events(feature_id: str):
    """
    Return every recorded run()/revise() request for this feature, oldest first -- the "ask"
    half of the frontend's per-stage activity timeline (paired with each artifact's own
    created_at as the "agent responded" half, and /approvals as the "reviewer decision" half).
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return stage_event_service.list_feature_events(feature_id)


@router.get("/features/{feature_id}/code/download")
def download_feature_code(feature_id: str):
    """
    Download this feature's actual generated code as a zip -- the real project the Coder Agent
    built, not its documentation artifacts (code_plan/code_diff/etc, already downloadable
    individually via GET /artifacts/{id}/download). Zips the feature's own branch if it still
    exists (so a reviewer can try the code locally before approving), otherwise `main` (the
    branch is deleted once merged).
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    try:
        content = workspace_service.export_feature_code_zip(feature["project_id"], feature_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    filename = f"{slugify(feature['feature_name'])}.zip"
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )