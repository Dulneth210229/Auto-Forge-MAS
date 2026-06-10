"""
Project routes.

A project is the main application being developed.

Example:
- E-commerce Platform
- LMS Platform

Each project can have many features.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.schemas.project_schema import ProjectCreateRequest, ProjectResponse
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id

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
    """
    return [
        ProjectResponse(**project)
        for project in store.projects.values()
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str):
    """
    Return one project by ID.
    """
    project = store.projects.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(**project)