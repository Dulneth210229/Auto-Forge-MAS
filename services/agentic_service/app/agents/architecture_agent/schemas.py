"""
Architecture Agent internal schemas.
"""

from pydantic import BaseModel


class ArchitectureAgentInput(BaseModel):
    project_id: str
    feature_id: str
    approved_srs_artifact_id: str
    approved_enhanced_srs_artifact_id: str
    human_comment: str | None = None


class ArchitectureAgentOutput(BaseModel):
    sds_markdown: str
    sds_json: dict
    api_contract_json: dict
    openapi_yaml: str
    usecase_puml: str