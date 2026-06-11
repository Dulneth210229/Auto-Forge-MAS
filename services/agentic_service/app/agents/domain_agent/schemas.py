"""
Domain Agent internal schemas.
"""

from pydantic import BaseModel


class DomainAgentInput(BaseModel):
    project_id: str
    feature_id: str
    approved_srs_artifact_id: str
    human_comment: str | None = None


class DomainAgentOutput(BaseModel):
    enhanced_srs_markdown: str
    enhanced_srs_json: dict
    domain_improvements_json: dict