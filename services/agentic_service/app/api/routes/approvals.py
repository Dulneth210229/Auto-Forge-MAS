"""
Approval routes.

These routes support Human-in-the-Loop approval.

The frontend will call these APIs when the user:
- approves an artifact
- rejects an artifact
- requests revision
"""

from fastapi import APIRouter, HTTPException

from app.schemas.approval_schema import ApprovalRequest, ApprovalResponse
from app.services.approval_service import approval_service
from app.services.in_memory_store import store

router = APIRouter(prefix="/artifacts", tags=["Approvals"])


@router.post("/{artifact_id}/approval", response_model=ApprovalResponse)
def submit_artifact_approval(artifact_id: str, request: ApprovalRequest
):
    """
    Submit approval decision for an artifact.

    request.status can be:
    - approved
    - rejected
    - revision_requested
    """
    artifact = store.artifacts.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    approval = approval_service.submit_approval(
        artifact_id=artifact_id,
        request=request
    )

    if not approval:
        raise HTTPException(status_code=400, detail="Approval failed")

    return approval