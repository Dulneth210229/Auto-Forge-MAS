"""
Approval schemas.

Approval gates are mandatory after every agent.

The backend should never allow the next agent to run unless
the previous required artifact is approved.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from app.core.enums import ApprovalStatus, AgentName


class ApprovalRequest(BaseModel):
    """
    Request body for approve, reject, or revision request.
    """
    status: ApprovalStatus = Field(..., example="approved")
    reviewer_comment: str | None = Field(
        default=None,
        example="Approved. Continue to the next agent."
    )
    approved_by: str = Field(default="human_user")


class ApprovalResponse(BaseModel):
    """
    API response after an approval action.
    """
    approval_id: str
    artifact_id: str
    agent_name: AgentName
    status: ApprovalStatus
    reviewer_comment: str | None
    approved_by: str
    approved_at: datetime