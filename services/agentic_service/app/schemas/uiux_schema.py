"""
UI/UX Agent API schema.
"""

from pydantic import BaseModel, Field


class UIUXAgentRunRequest(BaseModel):
    """
    Request body for running UI/UX Agent.
    """

    use_enhanced_srs_if_available: bool = Field(
        default=True,
        description="Use approved Enhanced SRS if it exists."
    )

    ui_preferences: dict = Field(
        default_factory=dict,
        description="Optional free-form UI preferences (theme, tone, layout hints).",
    )

    human_comment: str | None = Field(
        default=None,
        example="Generate UI metadata for the Login feature."
    )


class UIUXAgentReviseRequest(BaseModel):
    """
    Request body for revising already-generated UI/UX Agent output.
    """

    revision_comment: str = Field(
        ...,
        example="Add a 'no items found' empty state message to the item list component.",
    )

    revised_by: str | None = Field(
        default=None,
        description="Optional identifier of who requested the revision.",
    )
