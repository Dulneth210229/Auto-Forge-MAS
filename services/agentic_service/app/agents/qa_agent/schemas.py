"""
QA Agent internal schemas.

Placeholder shapes for this phase, mirroring DeploymentAgentInput/Output's
convention (project_id/feature_id + a report-shaped output) so the real
implementation can slot in later without a schema rewrite.
"""

from pydantic import BaseModel


class QAAgentInput(BaseModel):
    project_id: str
    feature_id: str
    approved_code_artifact_id: str


class QAAgentOutput(BaseModel):
    qa_report_json: dict = {}
    status: str = "skipped"
    message: str = "QA Agent not yet implemented."
