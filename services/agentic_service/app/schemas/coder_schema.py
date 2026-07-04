"""
Coder Agent API schema.
"""

from pydantic import BaseModel, Field


class CoderAgentRunRequest(BaseModel):
    """
    Request body for running Coder Agent.
    """

    use_enhanced_srs_if_available: bool = Field(
        default=True,
        description="Use approved Enhanced SRS if it exists."
    )

    human_comment: str | None = Field(
        default=None,
        example="Implement the Login feature."
    )
