"""
Security Agent internal schemas.
"""

from pydantic import BaseModel, Field


class SecurityAgentInput(BaseModel):
    """
    Internal input passed to the Security Agent.

    The Security Agent receives already-loaded project context and the
    outputs from previous agents. It does not load artifacts directly.
    """

    project: dict
    feature: dict

    # Approved Requirement Agent output
    srs_json: dict

    # Approved Architecture Agent output
    architecture_plan_json: dict

    # Approved Coder Agent outputs
    code_plan_json: dict
    code_manifest_json: dict
    requirement_code_map_json: dict

    # Optional human review comment
    human_comment: str | None = None


class SecurityAgentOutput(BaseModel):
    """
    Internal output produced by the Security Agent.
    """

    # Complete security report
    security_report_json: dict

    # High-level summary
    security_summary_json: dict

    # PASS / WARN / FAIL decision
    security_gate_json: dict

    # Fix recommendations
    fix_recommendations_json: dict

    # Human-readable report
    security_report_markdown: str

    # Artifact IDs registered by the Artifact Service
    artifact_ids: list[str] = Field(default_factory=list)