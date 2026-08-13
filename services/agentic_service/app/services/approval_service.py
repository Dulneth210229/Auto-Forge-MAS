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
# auto-start Architecture Agent against "the" approved version. ARCHITECTURE_PLAN joins for the
# same reason, per direct user request: only one Architecture Plan version is ever "the approved
# one". Deliberately narrow, not every gating artifact_type: e.g. UI/UX's ui_component_code
# artifacts are legitimately, independently approved several at a time (distinct components, not
# versions of one document).
EXCLUSIVE_VERSIONED_ARTIFACT_TYPES = {
    ArtifactType.SRS, ArtifactType.ENHANCED_SRS, ArtifactType.ARCHITECTURE_PLAN,
    ArtifactType.UI_PREVIEW_SCREENSHOT,
}

# The 3 diagram artifact types that ride along with every Architecture Plan generation, always
# sharing its exact version number (confirmed: _save_architecture_artifacts computes ONE version
# via get_next_version and reuses it for the plan's own JSON+Markdown pair AND all 3 diagrams'
# PUML+PNG pairs). Per direct user request, these no longer have their own independent approval
# decision -- approving/rejecting/requesting revision on the Architecture Plan cascades the same
# decision to every one of these, of the SAME version, automatically.
ARCHITECTURE_SIBLING_DIAGRAM_TYPES = {
    ArtifactType.USE_CASE_DIAGRAM, ArtifactType.SEQUENCE_DIAGRAM, ArtifactType.CLASS_DIAGRAM,
}

# Every UI/UX artifact type EXCEPT ui_preview_screenshot itself -- these no longer have their own
# independent approval decision either (per direct user request, mirroring the architecture
# diagram cascade above): approving/rejecting/requesting revision on the Preview Screenshot
# cascades the same decision to all of these, of the SAME version, automatically. A different
# page's screenshot (same version) is handled separately in the cascade itself, since it's the
# same type as the anchor artifact, not a "sibling type."
UIUX_SIBLING_ARTIFACT_TYPES = {
    ArtifactType.UI_METADATA, ArtifactType.UI_INTEGRATION_MANIFEST,
    ArtifactType.UI_COMPONENT_CODE, ArtifactType.UI_PAGE_HTML,
}


def _is_exclusive_versioned_type(artifact_type) -> bool:
    return any(
        artifact_type in (exclusive_type, exclusive_type.value)
        for exclusive_type in EXCLUSIVE_VERSIONED_ARTIFACT_TYPES
    )


def _is_architecture_plan_type(artifact_type) -> bool:
    return artifact_type in (ArtifactType.ARCHITECTURE_PLAN, ArtifactType.ARCHITECTURE_PLAN.value)


def _is_uiux_screenshot_type(artifact_type) -> bool:
    return artifact_type in (ArtifactType.UI_PREVIEW_SCREENSHOT, ArtifactType.UI_PREVIEW_SCREENSHOT.value)


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
                    # The reverted sibling is a DIFFERENT Architecture Plan version -- its own
                    # diagrams must revert too, or that old version's plan/diagram pair goes out
                    # of sync (plan back to pending, diagrams still showing approved).
                    if _is_architecture_plan_type(other.get("artifact_type")):
                        self._cascade_architecture_plan_decision(other, ApprovalStatus.PENDING)
                    # Same reasoning, UI/UX side: the reverted sibling is a DIFFERENT Preview
                    # Screenshot version -- its own metadata/manifest/components/page-html cascade
                    # must revert too, or that old version goes out of sync (screenshot back to
                    # pending, everything else still showing approved).
                    if _is_uiux_screenshot_type(other.get("artifact_type")):
                        self._cascade_uiux_screenshot_decision(other, ApprovalStatus.PENDING)

        # Approving/rejecting/requesting revision on the Architecture Plan applies the exact same
        # decision to its own Markdown/JSON sibling and all 3 diagram artifacts of the SAME
        # version -- per direct user request, diagrams no longer have an independent approval
        # decision at all. Fires on all three outcomes (not just approval), so self-gates on
        # artifact_type internally rather than being nested under is_approved/is_rejected below.
        self._cascade_architecture_plan_decision(artifact, request.status)

        # Same pattern, UI/UX side: approving/rejecting/requesting revision on the Preview
        # Screenshot applies the exact same decision to the underlying metadata, integration
        # manifest, every component, and every page-html artifact of the SAME version -- per
        # direct user request, these no longer have an independent approval decision either.
        self._cascade_uiux_screenshot_decision(artifact, request.status)

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
        # no separate "rollback" path to maintain. Triggers on either UI_METADATA
        # (the old, direct-approval target) or UI_PREVIEW_SCREENSHOT (the new one,
        # per direct user request) being the artifact DIRECTLY approved --
        # apply_design_system_patch resolves the actual UI_METADATA artifact by
        # version internally regardless of which one triggered the call.
        is_uiux_metadata_or_screenshot = (
            artifact["agent_name"] in [AgentName.UIUX, AgentName.UIUX.value]
            and artifact["artifact_type"] in [
                ArtifactType.UI_METADATA, ArtifactType.UI_METADATA.value,
                ArtifactType.UI_PREVIEW_SCREENSHOT, ArtifactType.UI_PREVIEW_SCREENSHOT.value,
            ]
        )

        if is_approved and is_uiux_metadata_or_screenshot:
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

    def _cascade_architecture_plan_decision(self, artifact: dict, status) -> None:
        """
        Applies `status` to every sibling artifact generated alongside this Architecture Plan
        artifact (its own other format -- JSON/Markdown -- plus all 3 diagram types, both PUML
        and PNG formats) that shares the SAME feature_id and SAME version. Self-gates on
        artifact_type (a no-op for anything that isn't an Architecture Plan artifact), so callers
        can invoke it unconditionally.

        Writes a synthetic approval record per cascaded sibling -- without one, a cascaded
        artifact would be a silent gap in list_feature_approvals (its status visibly changed but
        no record of why/when). approved_by is deliberately "system:architecture_plan_cascade",
        never the human's own name, so a future reader can immediately tell this wasn't an
        independent click -- matches this project's "report, don't misrepresent" convention (see
        Domain Agent's honest unmatched_operations reporting).

        Never raises: a cascade failure must not prevent the human's own approval action from
        succeeding, same precedent as every other post-approval hook in this file.
        """
        if not _is_architecture_plan_type(artifact.get("artifact_type")):
            return

        try:
            approved_at = datetime.utcnow()
            for sibling in store.artifacts.values():
                if sibling["artifact_id"] == artifact["artifact_id"]:
                    continue
                if sibling.get("feature_id") != artifact["feature_id"]:
                    continue
                if sibling.get("version") != artifact.get("version"):
                    continue

                is_other_plan_format = (
                    _is_architecture_plan_type(sibling.get("artifact_type"))
                    and sibling.get("artifact_format") != artifact.get("artifact_format")
                )
                is_diagram = any(
                    sibling.get("artifact_type") in (diagram_type, diagram_type.value)
                    for diagram_type in ARCHITECTURE_SIBLING_DIAGRAM_TYPES
                )
                if not (is_other_plan_format or is_diagram):
                    continue

                sibling["approval_status"] = status

                cascade_approval_id = generate_id("approval")
                store.approvals[cascade_approval_id] = {
                    "approval_id": cascade_approval_id,
                    "artifact_id": sibling["artifact_id"],
                    "feature_id": sibling["feature_id"],
                    "agent_name": sibling["agent_name"],
                    "status": status,
                    "reviewer_comment": (
                        f"Auto-{status.value if hasattr(status, 'value') else status} together "
                        f"with Architecture Plan v{artifact['version']} -- not an independent "
                        f"human decision."
                    ),
                    "approved_by": "system:architecture_plan_cascade",
                    "approved_at": approved_at,
                }
        except Exception:
            logger.exception(
                "Failed to cascade Architecture Plan decision for feature_id=%s version=%s",
                artifact.get("feature_id"),
                artifact.get("version"),
            )

    def _cascade_uiux_screenshot_decision(self, artifact: dict, status) -> None:
        """
        Applies `status` to every UI/UX sibling artifact of this Preview Screenshot -- the
        underlying ui_metadata (JSON+Markdown), ui_integration_manifest, every ui_component_code,
        every ui_page_html, AND any other ui_preview_screenshot (a different page) -- that shares
        the SAME feature_id and SAME version. Self-gates on artifact_type (a no-op for anything
        that isn't a Preview Screenshot artifact), so callers can invoke it unconditionally.
        Mirrors _cascade_architecture_plan_decision exactly -- same reasoning, same
        synthetic-approval-record convention, different anchor type.

        Writes a synthetic approval record per cascaded sibling -- without one, a cascaded
        artifact would be a silent gap in list_feature_approvals (its status visibly changed but
        no record of why/when). approved_by is deliberately "system:uiux_screenshot_cascade",
        never the human's own name, so a future reader can immediately tell this wasn't an
        independent click.

        Never raises: a cascade failure must not prevent the human's own approval action from
        succeeding, same precedent as every other post-approval hook in this file.
        """
        if not _is_uiux_screenshot_type(artifact.get("artifact_type")):
            return

        try:
            approved_at = datetime.utcnow()
            for sibling in store.artifacts.values():
                if sibling["artifact_id"] == artifact["artifact_id"]:
                    continue
                if sibling.get("feature_id") != artifact["feature_id"]:
                    continue
                if sibling.get("version") != artifact.get("version"):
                    continue

                is_sibling_type = any(
                    sibling.get("artifact_type") in (sibling_type, sibling_type.value)
                    for sibling_type in UIUX_SIBLING_ARTIFACT_TYPES
                )
                is_other_screenshot = _is_uiux_screenshot_type(sibling.get("artifact_type"))
                if not (is_sibling_type or is_other_screenshot):
                    continue

                sibling["approval_status"] = status

                cascade_approval_id = generate_id("approval")
                store.approvals[cascade_approval_id] = {
                    "approval_id": cascade_approval_id,
                    "artifact_id": sibling["artifact_id"],
                    "feature_id": sibling["feature_id"],
                    "agent_name": sibling["agent_name"],
                    "status": status,
                    "reviewer_comment": (
                        f"Auto-{status.value if hasattr(status, 'value') else status} together "
                        f"with Preview Screenshot v{artifact['version']} -- not an independent "
                        f"human decision."
                    ),
                    "approved_by": "system:uiux_screenshot_cascade",
                    "approved_at": approved_at,
                }
        except Exception:
            logger.exception(
                "Failed to cascade Preview Screenshot decision for feature_id=%s version=%s",
                artifact.get("feature_id"),
                artifact.get("version"),
            )

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