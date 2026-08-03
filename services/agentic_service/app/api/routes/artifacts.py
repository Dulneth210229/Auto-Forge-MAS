"""
Artifact routes.

These APIs allow users or frontend to:
- list artifacts for a feature
- view artifact metadata
- read an artifact's actual file content (text/JSON/image)
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from app.core.enums import ArtifactFormat
from app.schemas.artifact_schema import ArtifactResponse
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store

_DOWNLOAD_MEDIA_TYPES = {
    ArtifactFormat.PNG: "image/png",
    ArtifactFormat.JSON: "application/json",
    ArtifactFormat.MARKDOWN: "text/markdown",
}

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


@router.delete("/artifacts/{artifact_id}", status_code=204)
def delete_artifact(artifact_id: str):
    """
    Permanently delete one unapproved artifact version (e.g. a rejected/pending SRS revision a
    human wants to clear out of the version list). Refuses (400) to delete an approved artifact.
    """
    if not artifact_service.get_artifact(artifact_id):
        raise HTTPException(status_code=404, detail="Artifact not found")

    try:
        artifact_service.delete_artifact(artifact_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return Response(status_code=204)


@router.get("/artifacts/{artifact_id}/content")
def get_artifact_content(artifact_id: str):
    """
    Return an artifact's actual file content -- not just metadata.

    PNG artifacts are served as raw binary (image/png) so the frontend can use
    the URL directly in an <img src>. Everything else (markdown/json/text/code)
    is returned as a JSON body with the raw text always present, plus a
    best-effort parsed content_json when the format is "json" (never raises on
    a parse failure -- content_json is simply null in that case).
    """
    artifact = artifact_service.get_artifact(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if artifact.artifact_format == ArtifactFormat.PNG:
        return Response(content=artifact_service.read_artifact_binary(artifact_id), media_type="image/png")

    text = artifact_service.read_artifact_content(artifact_id)
    content_type = "json" if artifact.artifact_format == ArtifactFormat.JSON else "text"
    content_json = None

    if content_type == "json":
        try:
            content_json = json.loads(text)
        except ValueError:
            content_json = None

    return {
        "artifact_id": artifact_id,
        "artifact_format": artifact.artifact_format,
        "content_type": content_type,
        "content": text,
        "content_json": content_json,
    }


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str):
    """
    Download an artifact's raw file, exactly as generated -- sibling of /content (which wraps
    the same bytes in a JSON envelope for in-app viewing). This one sets Content-Disposition so
    a browser saves it as a real file instead of rendering/parsing it.
    """
    artifact = artifact_service.get_artifact(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    filename = Path(artifact.file_path).name
    media_type = _DOWNLOAD_MEDIA_TYPES.get(artifact.artifact_format, "text/plain")

    if artifact.artifact_format == ArtifactFormat.PNG:
        body = artifact_service.read_artifact_binary(artifact_id)
    else:
        body = artifact_service.read_artifact_content(artifact_id).encode("utf-8")

    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )