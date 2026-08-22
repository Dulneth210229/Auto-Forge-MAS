"""
QA Agent API schema.

No revise-request shape here, same reasoning as security_schema.py -- QA Agent has no "revise"
concept of its own; re-running IS the whole operation. "Fixing" a failing test happens on the
Coder Agent side (see coder_schema.py's CoderAgentReviseRequest, already unconstrained free text
-- no changes needed there to carry a QA report's findings).
"""

from pydantic import BaseModel, Field


class QAAgentRunRequest(BaseModel):
    """Mirrors SecurityAgentRunRequest exactly -- a single optional human_comment, recorded via
    stage_event_service for the activity log even though the agent itself doesn't consume it."""

    human_comment: str | None = Field(
        default=None,
        example="Re-run after the Coder Agent's latest revision.",
    )


class QAChatMessageRequest(BaseModel):
    """One human chat turn -- see agents.py's /qa/chat/stream route."""

    message: str = Field(..., example="Why did the item-listing unit test fail?")


class QAChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    created_at: str


class QAChatHistoryResponse(BaseModel):
    turns: list[QAChatTurn] = Field(default_factory=list)
