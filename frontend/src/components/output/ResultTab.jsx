import { useEffect, useState } from "react";
import { listGatingArtifactVersions } from "../../lib/deriveStageStatus";
import { ARTIFACT_TYPE_STAGE, STAGE_GATING_ARTIFACT, dedupeArtifactVersions } from "../../lib/artifactTypeMeta";
import { getEffectiveActiveArtifact } from "../../lib/activeArtifactSelection";
import { artifactDownloadUrl, featureCodeDownloadUrl } from "../../api/client";
import { declutterJsonForDisplay } from "../../lib/streamingJsonDisplay";
import ArtifactContentView from "../artifacts/ArtifactContentView";
import ArchitectureDiagramsGallery from "../pipeline/ArchitectureDiagramsGallery";
import UiuxPagePreviewsPanel from "../pipeline/UiuxPagePreviewsPanel";
import { LiveGenerationView } from "../pipeline/RequirementConversationParts";
import GovernancePanel from "../pipeline/GovernancePanel";
import ArtifactList from "../pipeline/ArtifactList";
import ErrorBanner from "../common/ErrorBanner";
import ConfirmDialog from "../common/ConfirmDialog";
import RequirementSrsOutputPanel from "./RequirementSrsOutputPanel";
import { useWorkspaceSelection } from "../workspace/WorkspaceSelectionContext";
import { useRequirementConversationFlowContext } from "../workspace/RequirementConversationFlowContext";
import { useDomainAgentFlowContext } from "../workspace/DomainAgentFlowContext";
import { useFeature, useSetActiveArtifactSelection } from "../../hooks/useFeatures";
import { useApprovalMutation } from "../../hooks/useApprovalMutation";

// Only the Requirement Agent's SRS -> Domain Agent handoff supports pinning a specific approved
// version today (direct user request) -- extend this map (mirrors OutputPanel's own) if another
// stage's handoff gets the same treatment.
const ACTIVE_SELECTION_ARTIFACT_TYPE_BY_STAGE = {
  requirement: "srs",
};

// domain_improvements is Domain Agent's own "what changed and why" side-record for the SAME
// version as its Enhanced SRS -- never independently meaningful and never what the pipeline gates
// on (STAGE_GATING_ARTIFACT only ever points at enhanced_srs for the domain stage; nothing in the
// backend ever reads domain_improvements' approval_status). It still gets saved with
// approval_status "pending" like every other artifact (artifact_service's generic default), which
// meant it showed up as its own row in "All Artifacts" with its own Approve/Reject/Request-
// Revision controls -- a real reported issue: the human was being asked to approve a document
// that was never a real decision point, on top of the Enhanced SRS itself. Excluded from the
// listed/approvable artifacts entirely; rendered instead as a read-only attachment directly under
// the Enhanced SRS document for the same version (see the domain-stage branch below).
const UNLISTED_ARTIFACT_TYPES = ["domain_improvements"];

// The Result tab: whichever agent is selected in the chat, this shows what it produced (version
// picker + document/diagram/screenshot view), plus governance (approve/reject, trace links) and
// the full versioned artifact list -- everything that used to live in StageOutputPanel +
// StageSidebar's Governance/Artifacts tabs, now scoped to the agent picked in the chat panel
// instead of a separate pipeline nav.
export default function ResultTab({ featureId, stage, allArtifacts }) {
  const { viewArtifact, selectAgent } = useWorkspaceSelection();
  const versions = listGatingArtifactVersions(stage, allArtifacts);
  const [selectedVersion, setSelectedVersion] = useState(versions[0]?.version ?? null);

  // Switching stages (e.g. auto-switching to Domain Agent right after approving the SRS) must
  // always jump to the NEW stage's latest version, unconditionally -- without this, a version
  // number that happens to exist for both stages (e.g. "v4" of both srs and enhanced_srs) would
  // pass the "does this version still exist" check below and silently keep showing the PREVIOUS
  // stage's document under the new stage's header, a real bug found live: the panel kept showing
  // an old SRS revision after switching to Domain Agent, simply because that version number
  // coincidentally also existed among Domain's own artifacts.
  useEffect(() => {
    setSelectedVersion(versions[0]?.version ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally NOT keyed on `versions`
    // here; that case (a new version arriving for the SAME stage) is handled by the effect below.
  }, [stage]);

  useEffect(() => {
    if (versions.length > 0 && !versions.some((v) => v.version === selectedVersion)) {
      setSelectedVersion(versions[0].version);
    }
  }, [versions, selectedVersion]);

  // While the Requirement Agent conversation is still in progress (no SRS artifact saved yet),
  // this is where its output belongs -- the same place every other stage's real output shows up,
  // instead of a second copy squeezed into the narrow chat column. RequirementSrsOutputPanel
  // deliberately shows nothing SRS-shaped (no template/draft preview) until real generation
  // starts -- see its own docstring.
  const isRequirementStage = stage === "requirement";

  // Always mounted regardless of stage (see RequirementConversationFlowProvider) -- cheap to read
  // unconditionally, only acted on when isRequirementStage. A revision streams the SAME way the
  // initial generation does: live in this panel, not a blocking wait then a static reveal (a real
  // reported issue), regardless of whether an approved SRS already exists.
  const { reviseStream, revisionStreamedText, revisionStreamStarted } = useRequirementConversationFlowContext();
  const isRevising = isRequirementStage && reviseStream.isPending;

  // Same idea for Domain Agent -- direct user report: Domain Agent had no live output at all
  // (blocking spinner, then a sudden reveal), the one agent left behind after every other
  // streamed flow already got this treatment. Domain's stream is the small enrichment PLAN (not
  // the final Enhanced SRS), decluttered for display -- same pragmatic choice
  // RequirementRevisionChat's own live view already makes (see LiveGenerationView's docstring):
  // shows something real and readable "typing" live, even though the actual merge into the
  // Enhanced SRS happens deterministically once the plan finishes, not token-by-token.
  const isDomainStage = stage === "domain";
  const {
    runStream: domainRunStream,
    runStreamedText: domainRunStreamedText,
    runStreamStarted: domainRunStreamStarted,
    reviseStream: domainReviseStream,
    revisionStreamedText: domainRevisionStreamedText,
    revisionStreamStarted: domainRevisionStreamStarted,
  } = useDomainAgentFlowContext();
  const isDomainRevising = isDomainStage && domainReviseStream.isPending;
  const isDomainRunning = isDomainStage && domainRunStream.isPending;
  const isDomainGenerating = isDomainRevising || isDomainRunning;
  const domainStreamedText = isDomainRevising ? domainRevisionStreamedText : domainRunStreamedText;
  const domainStreamStarted = isDomainRevising ? domainRevisionStreamStarted : domainRunStreamStarted;

  // Deduped for display: every gating artifact_type saves a JSON+Markdown pair sharing one
  // version, and listing both as separate rows read as the same version being duplicated (a real
  // reported issue) -- see dedupeArtifactVersions's own docstring.
  const stageArtifacts = dedupeArtifactVersions(
    allArtifacts.filter(
      (a) => ARTIFACT_TYPE_STAGE[a.artifact_type] === stage && !UNLISTED_ARTIFACT_TYPES.includes(a.artifact_type)
    )
  );

  // Lets a human pin which APPROVED version feeds the next agent (e.g. which SRS version Domain
  // Agent reads) instead of always the latest approved one -- see ArtifactRow's radio button and
  // OutputPanel's "Using SRS vN for Domain Agent" indicator, which reads the same effective value.
  const { data: feature } = useFeature(featureId);
  const setActiveSelection = useSetActiveArtifactSelection(featureId);
  const activeArtifactType = ACTIVE_SELECTION_ARTIFACT_TYPE_BY_STAGE[stage];
  const effectiveActiveArtifact = activeArtifactType
    ? getEffectiveActiveArtifact(allArtifacts, feature?.active_artifact_selection, activeArtifactType)
    : null;

  // Approving the Requirement Agent's SRS is the one stage where approving genuinely switches the
  // human's chat over to a different agent -- worth an explicit confirmation, not just an
  // immediate click. Owned HERE (not inside GovernancePanel or ArtifactRow) because BOTH of those
  // can offer an Approve button for a pending SRS version now (a real reported bug: only the
  // single "operative"/highest-version artifact ever had approval controls at all) -- this is
  // their shared ancestor, and it never unmounts across the approve -> switch-chat transition the
  // way either child can (see this component's own git history for the exact unmount bug this
  // already caused once).
  //
  // Deliberately does NOT auto-run Domain Agent anymore (it used to, immediately, with an empty
  // human_comment) -- a real, direct user report: Domain Agent already running blind, before the
  // human ever got a chance to say "use existing domain knowledge" vs. "here's a database schema
  // I want incorporated," meant their only option once they arrived at its chat was to REVISE
  // already-generated output instead of guiding the ORIGINAL generation. Approving now only
  // switches the chat to Domain Agent; ChatPanel's own empty-state prompt (see its own comment)
  // is what invites the human to guide the actual first run.
  const isSrsApproval = stage === "requirement";
  const [confirmingArtifactId, setConfirmingArtifactId] = useState(null);
  const srsApproval = useApprovalMutation(featureId);

  function requestSrsApproveConfirmation(artifactId) {
    setConfirmingArtifactId(artifactId);
  }

  async function handleConfirmedSrsApprove() {
    try {
      await srsApproval.mutateAsync({ artifactId: confirmingArtifactId, status: "approved" });
    } catch {
      // Keep the dialog open -- srsApproval.error is rendered inside it so the human can see why
      // and retry or cancel, instead of the dialog vanishing on a failed approval.
      return;
    }

    setConfirmingArtifactId(null);
    selectAgent("domain");
  }

  const confirmingArtifact = confirmingArtifactId
    ? stageArtifacts.find((a) => a.artifact_id === confirmingArtifactId)
    : null;

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">
          All Artifacts ({stageArtifacts.length})
        </h3>
        <ErrorBanner error={setActiveSelection.error} fallback="Failed to change which version is in use." />
        <ArtifactList
          artifacts={stageArtifacts}
          onView={viewArtifact}
          // Only used to gate the (separate, revise-only) Revise button -- approval controls are
          // no longer suppressed for any row of the gating type (see ArtifactList's docstring).
          gatingArtifactType={STAGE_GATING_ARTIFACT[stage]?.type ?? null}
          featureId={featureId}
          onApproveClick={isSrsApproval ? requestSrsApproveConfirmation : undefined}
          activeArtifactType={activeArtifactType}
          activeArtifactId={effectiveActiveArtifact?.artifact_id}
          settingActive={setActiveSelection.isPending}
          onSetActive={(artifactId) =>
            setActiveSelection.mutate({ artifact_type: activeArtifactType, artifact_id: artifactId })
          }
        />
      </div>

      {isRevising ? (
        <LiveGenerationView
          displayText={declutterJsonForDisplay(revisionStreamedText)}
          hasStarted={revisionStreamStarted}
          connectingLabel="Connecting to Requirement Agent..."
          generatingLabel="Reviewing your requested change..."
        />
      ) : isDomainGenerating ? (
        <LiveGenerationView
          displayText={declutterJsonForDisplay(domainStreamedText)}
          hasStarted={domainStreamStarted}
          connectingLabel="Connecting to Domain Agent..."
          generatingLabel={isDomainRevising ? "Applying your requested change..." : "Enriching the SRS with domain knowledge..."}
        />
      ) : versions.length === 0 && isRequirementStage ? (
        <RequirementSrsOutputPanel />
      ) : versions.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500 italic">No output yet for this stage.</p>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-3">
            <select
              value={selectedVersion ?? ""}
              onChange={(e) => setSelectedVersion(Number(e.target.value))}
              className="text-sm border border-gray-300 dark:border-gray-600 dark:bg-white/5 dark:text-gray-100 rounded-md p-1.5 focus:outline-none focus:border-accent-500"
            >
              {versions.map((v) => (
                <option key={v.artifact_id} value={v.version} className="dark:bg-gray-800">
                  v{v.version} -- {v.approval_status}
                </option>
              ))}
            </select>
            <div className="flex items-center gap-3">
              {(() => {
                const artifact = versions.find((v) => v.version === selectedVersion) || versions[0];
                return (
                  <a
                    href={artifactDownloadUrl(artifact.artifact_id)}
                    className="text-sm text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300 font-semibold"
                  >
                    Download report
                  </a>
                );
              })()}
              {stage === "coder" && (
                <a
                  href={featureCodeDownloadUrl(featureId)}
                  className="text-sm bg-accent-600 hover:bg-accent-700 text-white font-semibold px-3 py-1.5 rounded-md"
                >
                  Download Project (.zip)
                </a>
              )}
            </div>
          </div>

          {stage === "uiux" ? (
            <UiuxPagePreviewsPanel allArtifacts={allArtifacts} />
          ) : (
            (() => {
              const artifact = versions.find((v) => v.version === selectedVersion) || versions[0];
              // Domain Improvements attaches to whichever Enhanced SRS version is being viewed --
              // same version number (both saved together, see domain_agent's _save_domain_artifacts),
              // never its own listed/approvable row (see UNLISTED_ARTIFACT_TYPES above).
              const domainImprovements =
                stage === "domain"
                  ? allArtifacts.find(
                      (a) => a.artifact_type === "domain_improvements" && a.version === artifact.version
                    )
                  : null;
              return (
                <div>
                  <ArtifactContentView artifact={artifact} domainImprovementsArtifact={domainImprovements} />
                  {stage === "architecture" && <ArchitectureDiagramsGallery allArtifacts={allArtifacts} />}
                  {domainImprovements && (
                    <div className="mt-5 pt-5 border-t border-gray-100 dark:border-gray-800">
                      <ArtifactContentView artifact={domainImprovements} />
                    </div>
                  )}
                </div>
              );
            })()
          )}
        </div>
      )}

      <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
        <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">Governance</h3>
        <GovernancePanel
          stage={stage}
          featureId={featureId}
          allArtifacts={allArtifacts}
          stageArtifacts={stageArtifacts}
          onApproveClick={isSrsApproval ? requestSrsApproveConfirmation : undefined}
        />
      </div>

      {isSrsApproval && (
        <ConfirmDialog
          open={Boolean(confirmingArtifactId)}
          onClose={() => {
            if (!srsApproval.isPending) setConfirmingArtifactId(null);
          }}
          onConfirm={handleConfirmedSrsApprove}
          title="Approve this SRS and continue to Domain Agent?"
          message={`Approving v${confirmingArtifact?.version} makes it the SRS this feature uses going forward (any other approved SRS version is superseded back to pending). Your chat will switch to Domain Agent, where you can tell it how to enrich this SRS -- using existing domain knowledge, something specific you provide, or both.`}
          confirmLabel="Approve & Continue"
          confirmingLabel="Approving..."
          tone="primary"
          confirming={srsApproval.isPending}
          error={srsApproval.error}
          errorFallback="Failed to submit approval decision."
        />
      )}
    </div>
  );
}
