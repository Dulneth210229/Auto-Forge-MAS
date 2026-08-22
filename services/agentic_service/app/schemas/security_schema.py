"""
Security Agent API schema.

No revise-request shape here, unlike every other agent's schema file -- the Security Agent has
no "revise" concept of its own: re-running IS the whole operation, and what the human calls a
"revision" happens on the Coder Agent side (see coder_schema.py's CoderAgentReviseRequest,
already unconstrained free text with no changes needed to carry a security report's findings).
"""

from pydantic import BaseModel, Field


class SecurityAgentRunRequest(BaseModel):
    """
    Request body for running the Security Agent -- mirrors every other agent's run-request
    shape (a single optional human_comment, recorded via stage_event_service for the activity
    log) even though the agent itself doesn't consume it yet.
    """

    human_comment: str | None = Field(
        default=None,
        example="Re-scan after the Coder Agent's latest revision.",
    )
