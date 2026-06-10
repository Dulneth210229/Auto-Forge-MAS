"""
Project schemas.

These Pydantic models define the request and response shape
for project-related APIs.

A project represents the full target application, such as:
- E-commerce Platform
- LMS Platform
- CRM System
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """
    Request body for creating a project.
    """
    project_name: str = Field(..., example="E-commerce Platform")
    project_type: str = Field(..., example="E-commerce")
    target_stack: str = Field(default="MERN", example="MERN")
    created_by: str = Field(default="human_user", example="ba_user")


class ProjectResponse(BaseModel):
    """
    API response returned after creating or reading a project.
    """
    project_id: str
    project_name: str
    project_type: str
    target_stack: str
    created_by: str
    created_at: datetime
    updated_at: datetime