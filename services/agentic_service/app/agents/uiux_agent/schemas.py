"""
UI/UX Agent internal schemas.
"""

from pydantic import BaseModel


class UIUXAgentInput(BaseModel):
    project_id: str
    feature_id: str
    approved_srs_artifact_id: str
    approved_enhanced_srs_artifact_id: str
    approved_sds_artifact_id: str
    ui_preferences: dict = {}
    human_comment: str | None = None


class UIUXAgentOutput(BaseModel):
    ui_design_markdown: str
    ui_metadata_json: dict
    html_tailwind: str
    react_component: str | None = None