"""
Approval service.

This handles human approval decisions.

Important rule:
No agent output should move to the next agent unless the artifact is approved.
"""

from datetime import datetime

from app.agents.coder_agent.agent import coder_agent
from app.agents.uiux_agent.agent import uiux_agent
from app.core.enums import AgentName, ApprovalStatus, ArtifactType
from app.schemas.approval_schema import ApprovalRequest, ApprovalResponse
from app.services.graph_orchestrator_service import (
    GraphNotRunningError,
    graph_orchestrator_service,
)
from app.services.in_memory_store import store
from app.utils.id_generator import generate_id
from app.utils.logger import get_logger

logger = get_logger(__name__)


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

        # If this artifact belongs to a feature with an active graph run paused on
        # an approval gate, advance it. Most artifacts today are still approved
        # through the legacy manual flow (no graph run started via
        # POST /features/{id}/start), so a missing/mismatched paused run is
        # expected and not an error.
        try:
            graph_orchestrator_service.resume(
                feature_id=artifact["feature_id"],
                resume_value=request.status.value,
            )
        except GraphNotRunningError:
            pass
        except Exception:
            logger.exception(
                "Failed to resume graph run for feature_id=%s after approval",
                artifact["feature_id"],
            )

        # UI/UX Agent: merge new components/tokens into the project's shared
        # design_system.json, but only now that this exact version has been
        # approved -- a rejected run must never reach this line, so there is
        # no separate "rollback" path to maintain.
        is_approved = request.status in [ApprovalStatus.APPROVED, ApprovalStatus.APPROVED.value]
        is_uiux_metadata = (
            artifact["agent_name"] in [AgentName.UIUX, AgentName.UIUX.value]
            and artifact["artifact_type"] in [ArtifactType.UI_METADATA, ArtifactType.UI_METADATA.value]
        )

        if is_approved and is_uiux_metadata:
            try:
                uiux_agent.apply_design_system_patch(
                    feature_id=artifact["feature_id"],
                    version=artifact["version"],
                )
            except Exception:
                logger.exception(
                    "Failed to apply design system patch for feature_id=%s version=%s",
                    artifact["feature_id"],
                    artifact["version"],
                )

        # Coder Agent: merge the approved feature branch into main and update
        # project_manifest.json, or discard the branch on rejection -- gated
        # on this exact artifact/version, same discipline as the UI/UX hook
        # above. Never merges automatically regardless of verification result;
        # that's the human's call, informed by merge_report_markdown.
        is_rejected = request.status in [ApprovalStatus.REJECTED, ApprovalStatus.REJECTED.value]
        is_coder_diff = (
            artifact["agent_name"] in [AgentName.CODER, AgentName.CODER.value]
            and artifact["artifact_type"] in [ArtifactType.CODE_DIFF, ArtifactType.CODE_DIFF.value]
        )

        if is_coder_diff and is_approved:
            try:
                coder_agent.merge_approved_feature(
                    feature_id=artifact["feature_id"],
                    version=artifact["version"],
                )
            except Exception:
                logger.exception(
                    "Failed to merge approved feature for feature_id=%s version=%s",
                    artifact["feature_id"],
                    artifact["version"],
                )
        elif is_coder_diff and is_rejected:
            try:
                coder_agent.discard_rejected_feature(feature_id=artifact["feature_id"])
            except Exception:
                logger.exception(
                    "Failed to discard rejected feature branch for feature_id=%s",
                    artifact["feature_id"],
                )

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