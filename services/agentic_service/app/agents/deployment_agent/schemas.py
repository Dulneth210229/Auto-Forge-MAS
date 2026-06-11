"""
Deployment Agent internal schemas.
"""

from pydantic import BaseModel


class DeploymentAgentInput(BaseModel):
    project_id: str
    feature_id: str
    approved_code_artifact_id: str
    env_vars_reference: dict = {}
    deployment_target: str = "local"


class DeploymentAgentOutput(BaseModel):
    deployment_status_json: dict
    build_logs: str
    runtime_logs: str
    error_logs: str | None = None
    preview_url_json: dict | None = None