"""
Security Agent internal schemas.
"""

from pydantic import BaseModel, Field


class SecurityAgentOutput(BaseModel):
    """
    Internal output produced by the Security Agent.

    This model represents the complete security analysis results before
    they are saved as artifacts.
    """

    # Complete security report
    security_report_json: dict

    # Security Gate result
    security_gate_json: dict

    # Human-readable Markdown report
    security_report_markdown: str

    # Artifact IDs created by the Artifact Service
    artifact_ids: list[str] = Field(default_factory=list)