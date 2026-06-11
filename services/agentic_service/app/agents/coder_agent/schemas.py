"""
Coder Agent internal schemas.
"""

from pydantic import BaseModel


class CoderAgentInput(BaseModel):
    project_id: str
    feature_id: str
    approved_srs_artifact_id: str
    approved_enhanced_srs_artifact_id: str
    approved_sds_artifact_id: str
    approved_uiux_artifact_id: str
    env_vars_reference: dict = {}
    human_comment: str | None = None


class CoderAgentOutput(BaseModel):
    file_tree_json: dict
    code_manifest_json: dict
    requirement_code_map_json: dict
    setup_instructions_markdown: str
    merge_report_markdown: str