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

# Artifact types that are singleton documents-with-versions, where only one version may hold
# "approved" at a time -- approving a new version supersedes whichever OTHER version (if any) was
# previously approved for this feature, reverting it back to "pending". Direct user report: seeing
# two SRS versions simultaneously "Approved" was confusing (which one does Domain Agent actually
# use?) -- ENHANCED_SRS joins this set for the exact same reason, now that approving it can
# auto-start Architecture Agent against "the" approved version. Deliberately narrow, not every
# gating artifact_type: e.g. UI/UX's ui_component_code artifacts are legitimately, independently
# approved several at a time (distinct components, not versions of one document).
EXCLUSIVE_VERSIONED_ARTIFACT_TYPES = {ArtifactType.SRS, ArtifactType.ENHANCED_SRS}


def _is_exclusive_versioned_type(artifact_type) -> bool:
    return any(
        artifact_type in (exclusive_type, exclusive_type.value)
        for exclusive_type in EXCLUSIVE_VERSIONED_ARTIFACT_TYPES
    )


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
            "feature_id": artifact["feature_id"],
            "agent_name": artifact["agent_name"],
            "status": request.status,
            "reviewer_comment": request.reviewer_comment,
            "approved_by": request.approved_by,
            "approved_at": approved_at,
        }

        store.approvals[approval_id] = approval

        # Update artifact status directly.
        artifact["approval_status"] = request.status

        is_approved = request.status in [ApprovalStatus.APPROVED, ApprovalStatus.APPROVED.value]

        # See EXCLUSIVE_VERSIONED_ARTIFACT_TYPES's own docstring for why SRS/Enhanced SRS get this
        # rule. Reverts only a sibling of the SAME artifact_type (never cross-type -- approving an
        # Enhanced SRS must never revert the plain SRS the pipeline still needs approved) AND the
        # SAME artifact_format (a real, previously-reported gap: without this, approving the JSON
        # half of one version could silently revert the Markdown half of a DIFFERENT already-
        # approved version's sibling row, or vice versa, since every gating type saves a JSON+
        # Markdown pair sharing one version number -- see CLAUDE.md's own note on this).
        should_check_exclusivity = is_approved and _is_exclusive_versioned_type(artifact["artifact_type"])

        if should_check_exclusivity:
            for other in store.artifacts.values():
                if other["artifact_id"] == artifact_id:
                    continue
                if other.get("feature_id") != artifact["feature_id"]:
                    continue
                if other.get("artifact_type") != artifact["artifact_type"]:
                    continue
                if other.get("artifact_format") != artifact.get("artifact_format"):
                    continue
                if other.get("approval_status") in [ApprovalStatus.APPROVED, ApprovalStatus.APPROVED.value]:
                    other["approval_status"] = ApprovalStatus.PENDING

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

    def list_feature_approvals(self, feature_id: str) -> list[ApprovalResponse]:
        """
        Return every approval decision recorded for a feature, oldest first -- powers the
        frontend's per-stage activity timeline (a real, chronological record of what was
        approved/rejected/revision-requested and when, not a reconstruction).

        Matches via each approval's OWN artifact's feature_id, not the approval's own
        `feature_id` field (added in submit_approval going forward) -- every approval ever made
        before that field existed would otherwise be permanently invisible here, and this
        feature's entire pre-existing approval history is exactly that case. The artifact join
        works identically for old and new records, so it's used unconditionally rather than as a
        fallback.
        """
        results = []

        for approval in store.approvals.values():
            artifact = store.artifacts.get(approval.get("artifact_id"))

            if not artifact or artifact.get("feature_id") != feature_id:
                continue

            try:
                results.append(ApprovalResponse(**approval))
            except Exception:
                logger.warning("Skipping unparseable approval %s", approval.get("approval_id"))

        results.sort(key=lambda a: a.approved_at)
        return results

    def is_artifact_approved(self, artifact_id: str) -> bool:
        """
        Check whether an artifact has been approved.
        """
        artifact = store.artifacts.get(artifact_id)

        if not artifact:
            return False

        return artifact["approval_status"] == ApprovalStatus.APPROVED


approval_service = ApprovalService()