"""
Requirement Agent internal schemas.

These schemas will be used only by Requirement Agent.
"""

from pydantic import BaseModel


class RequirementAgentInput(BaseModel):
    project_id: str
    feature_id: str
    human_comment: str | None = None


class RequirementAgentOutput(BaseModel):
    srs_markdown: str
    srs_json: dict