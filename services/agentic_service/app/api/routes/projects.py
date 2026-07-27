"""
Project routes.

A project is the main application being developed.

Example:
- E-commerce Platform
- LMS Platform

Each project can have many features.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Response
from pydantic import ValidationError

from app.schemas.project_schema import ProjectCreateRequest, ProjectResponse
from app.services.in_memory_store import store
from app.services.workspace_service import workspace_service
from app.utils.id_generator import generate_id
from app.utils.logger import get_logger
from app.utils.slugify import slugify

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse)
def create_project(request: ProjectCreateRequest):
    """
    Create a new project.

    This is the first step before creating features.
    """
    now = datetime.utcnow()
    project_id = generate_id("proj")

    project = {
        "project_id": project_id,
        "project_name": request.project_name,
        "project_type": request.project_type,
        "target_stack": request.target_stack,
        "created_by": request.created_by,
        "created_at": now,
        "updated_at": now,
    }

    store.projects[project_id] = project

    return ProjectResponse(**project)


@router.get("", response_model=list[ProjectResponse])
def list_projects():
    """
    Return all created projects.

    Skips (and logs a warning for) any individual record that fails to validate -- a
    malformed/legacy project document should not break this list for every other, valid
    project.
    """
    results = []

    for project in store.projects.values():
        try:
            results.append(ProjectResponse(**project))
        except ValidationError as error:
            logger.warning("Skipping unparseable project %s: %s", project.get("project_id"), error)

    return results


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str):
    """
    Return one project by ID.
    """
    project = store.projects.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(**project)


@router.get("/{project_id}/code/download")
def download_project_code(project_id: str):
    """
    Download the project's cumulative generated app (main branch) as a zip -- every feature
    merged into main so far, combined.
    """
    project = store.projects.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        content = workspace_service.export_zip(project_id, "main")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    filename = f"{slugify(project['project_name'])}.zip"
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )