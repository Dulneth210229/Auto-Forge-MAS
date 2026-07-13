"""
Security Agent API schema.
"""

from pydantic import BaseModel, Field


class SecurityAgentRunRequest(BaseModel):
    """
    Request body for running the Security Agent.
    """

    enable_llm_review: bool = Field(
        default=True,
        description="Enable LLM-assisted security review."
    )

    human_comment: str | None = Field(
        default=None,
        example="Perform a complete security review before QA."
    )


class SecurityAgentReviseRequest(BaseModel):
    """
    Request body for revising the latest Security Agent output.
    """

    revision_comment: str = Field(
        ...,
        example="Re-run security validation after fixing vulnerabilities."
    )

    revised_by: str = Field(
        default="human_user",
        example="human_user"
    )