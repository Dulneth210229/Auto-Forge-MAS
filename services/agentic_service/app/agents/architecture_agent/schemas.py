"""
Architecture Agent internal schemas.

These schemas are used only inside the Architecture Agent.

The agent receives approved SRS and Enhanced SRS.
It outputs SDS and Use Case Diagram artifacts.

Important:
This version does NOT generate API contract or OpenAPI YAML.
"""

from pydantic import BaseModel, Field


class ArchitectureAgentInput(BaseModel):
    """
    Input required to run the Architecture Agent.
    """

    project_id: str
    feature_id: str

    # Approved artifacts from previous agents.
    approved_srs_markdown: str
    approved_enhanced_srs_markdown: str

    # Basic project context.
    project_type: str
    feature_name: str
    target_stack: str

    # Optional human revision comment.
    human_comment: str | None = None


class ArchitectureAgentOutput(BaseModel):
    """
    Output returned by the Architecture Agent.

    These fields are saved as versioned artifacts.
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
        description="Mapping between requirements and architecture decisions."
    )