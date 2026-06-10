"""
Artifact routes.

These APIs allow users or frontend to:
- list artifacts for a feature
- view artifact metadata
"""

from fastapi import APIRouter, HTTPException

from app.schemas.artifact_schema import ArtifactResponse
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store

router = APIRouter(tags=["Artifacts"])


@router.get("/features/{feature_id}/artifacts", response_model=list[ArtifactResponse])
def list_feature_artifacts(feature_id: str):
    """
    Return all artifacts generated for a feature.
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return artifact_service.list_feature_artifacts(feature_id)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(artifact_id: str):
    """
    Return artifact metadata by artifact ID.
    """
    artifact = artifact_service.get_artifact(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return artifact