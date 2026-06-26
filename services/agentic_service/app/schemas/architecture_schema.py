"""
Architecture Agent API schemas.

This file defines the request body used when running the Architecture Agent.

The Architecture Agent should generate:
- SDS JSON
- SDS Markdown
- Use Case Diagram PlantUML
- Use Case Diagram PNG

Important:
The user asked not to generate API contract.
So this schema does not include API contract options.
"""

from pydantic import BaseModel, Field


class ArchitectureAgentRunRequest(BaseModel):
    """
    Request body for running Architecture Agent.

    use_enhanced_srs_if_available:
        If Domain Agent has already generated an approved Enhanced SRS,
        Architecture Agent can use it.
        If not available, it will use the approved SRS.

    architecture_notes:
        Optional human instruction.
        Example:
        "Use MVC style for this Login feature."

    human_comment:
        Optional comment from the user.
    """

    use_enhanced_srs_if_available: bool = Field(
        default=True,
        description="Use approved Enhanced SRS if it exists."
    )

    architecture_notes: str | None = Field(
        default=None,
        example="Use MVC style and keep the feature simple for MERN implementation."
    )

    human_comment: str | None = Field(
        default=None,
        example="Generate SDS and use case diagram for Login feature."
    )