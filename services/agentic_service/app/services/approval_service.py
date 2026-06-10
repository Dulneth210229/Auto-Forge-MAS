"""
Approval service.

This handles human approval decisions.

Important rule:
No agent output should move to the next agent unless the artifact is approved.
"""

from datetime import datetime

from app.core.enums import ApprovalStatus
from app.schemas.approval_schema import ApprovalRequest, ApprovalResponse
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id


class ApprovalService:
    """
    Handles approve, reject, and revision request logic.
    """

    def submit_approval(self, artifact_id: str,  request: ApprovalRequest) -> ApprovalResponse | None:
        """
        Save approval decision for an artifact.

        Also updates the artifact approval_status.
        """
        artifact = store.artifacts.get(artifact_id)

        if not artifact:
            return None

        approval_id = generate_id("approval")
        approved_at = datetime.utcnow()

        approval = {
            "approval_id": approval_id,
            "artifact_id": artifact_id,
            "agent_name": artifact["agent_name"],
            "status": request.status,
            "reviewer_comment": request.reviewer_comment,
            "approved_by": request.approved_by,
            "approved_at": approved_at,
        }

        store.approvals[approval_id] = approval

        # Update artifact status directly.
        artifact["approval_status"] = request.status

        return ApprovalResponse(**approval)

    def is_artifact_approved(self, artifact_id: str) -> bool:
        """
        Check whether an artifact has been approved.
        """
        artifact = store.artifacts.get(artifact_id)

        if not artifact:
            return False

        return artifact["approval_status"] == ApprovalStatus.APPROVED


approval_service = ApprovalService()