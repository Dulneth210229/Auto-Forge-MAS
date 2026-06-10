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

from fastapi import APIRouter, HTTPException

from app.core.enums import FeatureStatus, AgentName
from app.schemas.feature_schema import FeatureCreateRequest, FeatureResponse
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id

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
    """
    project = store.projects.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return [
        FeatureResponse(**feature)
        for feature in store.features.values()
        if feature["project_id"] == project_id
    ]


@router.get("/features/{feature_id}", response_model=FeatureResponse)
def get_feature(feature_id: str):
    """
    Return one feature by ID.
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return FeatureResponse(**feature)