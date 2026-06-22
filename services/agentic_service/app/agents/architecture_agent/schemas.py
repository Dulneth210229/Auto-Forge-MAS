"""
Architecture Agent internal schemas.

The Architecture Agent receives approved JSON artifacts from:
- Requirement Agent: SRS JSON
- Domain Agent: Enhanced SRS JSON

Why JSON?
- JSON is machine-readable.
- JSON contains stable requirement IDs such as FR-001, AC-001, BR-001.
- Architecture traceability should be based on these IDs.
"""

from pydantic import BaseModel, Field


class ArchitectureAgentInput(BaseModel):
    """
    Input required to run the Architecture Agent.

    This version uses JSON artifacts, not Markdown artifacts.
    """

    project_id: str
    feature_id: str

    # Approved JSON artifacts from previous agents.
    approved_srs_json: dict
    approved_enhanced_srs_json: dict

    # Basic project context.
    project_type: str
    feature_name: str
    target_stack: str

    # Optional comment only for revision cases.
    human_comment: str | None = None


class ArchitectureAgentOutput(BaseModel):
    """
    Output returned by the Architecture Agent.
    """

    sds_markdown: str = Field(
        ...,
        description="Human-readable Software Design Specification."
    )

    sds_json: dict = Field(
        ...,
        description="Machine-readable Software Design Specification."
    )

    usecase_puml: str = Field(
        ...,
        description="PlantUML source for the Use Case Diagram."
    )

    traceability_json: dict = Field(
        ...,
        description="Mapping between requirement IDs and architecture decisions."
    )