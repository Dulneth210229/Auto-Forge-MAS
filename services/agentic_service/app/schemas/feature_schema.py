"""
Feature schemas.

A feature is one SDLC unit.

Examples:
- Login
- Signup
- Product Listing
- Cart
- Checkout

Each feature goes through all agents one by one.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from app.core.enums import FeatureStatus, AgentName


class FeatureCreateRequest(BaseModel):
    """
    Request body for creating a new feature inside a project.
    """
    feature_name: str = Field(..., example="Login")
    feature_description: str = Field(
        ...,
        example="Allow users to login using email and password."
    )


class FeatureResponse(BaseModel):
    """
    API response for a feature.
    """
    feature_id: str
    project_id: str
    feature_name: str
    feature_description: str
    feature_status: FeatureStatus
    current_agent: AgentName | None
    created_at: datetime
    updated_at: datetime