import { useEffect, useRef, useState } from "react";
import { listGatingArtifactVersions } from "../../lib/deriveStageStatus";
import { ARTIFACT_TYPE_STAGE, STAGE_GATING_ARTIFACT, dedupeArtifactVersions } from "../../lib/artifactTypeMeta";
import { getEffectiveActiveArtifact } from "../../lib/activeArtifactSelection";
import { artifactDownloadUrl, featureCodeDownloadUrl } from "../../api/client";
import { declutterJsonForDisplay } from "../../lib/streamingJsonDisplay";
import { looksLikeMongoUri } from "../../lib/mongoUri";
import ArtifactContentView from "../artifacts/ArtifactContentView";
import ArchitectureDiagramsGallery from "../pipeline/ArchitectureDiagramsGallery";
import UiuxPagePreviewsPanel from "../pipeline/UiuxPagePreviewsPanel";
import { LiveGenerationView } from "../pipeline/RequirementConversationParts";
import GovernancePanel from "../pipeline/GovernancePanel";
import ApprovalPanel from "../pipeline/ApprovalPanel";
import ArtifactList from "../pipeline/ArtifactList";
import UiuxVersionGroupList from "../pipeline/UiuxVersionGroupList";
import ErrorBanner from "../common/ErrorBanner";
import ConfirmDialog from "../common/ConfirmDialog";
import RequirementSrsOutputPanel from "./RequirementSrsOutputPanel";
import SecurityReportView from "../security/SecurityReportView";
import SecurityDecisionDialog from "../security/SecurityDecisionDialog";
import QaReportView from "../qa/QaReportView";
import { useWorkspaceSelection } from "../workspace/WorkspaceSelectionContext";
import { useRequirementConversationFlowContext } from "../workspace/RequirementConversationFlowContext";
import { useDomainAgentFlowContext } from "../workspace/DomainAgentFlowContext";
import { useArchitectureAgentFlowContext } from "../workspace/ArchitectureAgentFlowContext";
import { useUiuxAgentFlowContext } from "../workspace/UiuxAgentFlowContext";
import { useCoderAgentFlowContext } from "../workspace/CoderAgentFlowContext";
import { useFeature, useSetActiveArtifactSelection } from "../../hooks/useFeatures";
import { useApprovalMutation } from "../../hooks/useApprovalMutation";

// Both Requirement->Domain and Domain->Architecture support pinning a specific approved version
// (direct user request for the latter, mirroring the former) -- extend this map (mirrors
// OutputPanel's own) if another stage's handoff gets the same treatment.
const ACTIVE_SELECTION_ARTIFACT_TYPE_BY_STAGE = {
  requirement: "srs",
  domain: "enhanced_srs",
};

// Drives the "Approve and continue" popup + orchestration for the three stage transitions that
// need it -- one config, one confirmingArtifactId state, one ConfirmDialog, instead of a separate
// parallel block per stage duplicating requirement's own. `autoRun: true` means confirming
// doesn't just switch the chat -- it also starts the next agent immediately, no separate manual
// click needed (a deliberate, different UX from Requirement -> Domain, where a human explicitly
// guides the very first run instead -- see ChatPanel's own proactive Domain Agent prompt).
// Domain -> Architecture's autoRun starts a real STREAM (handleRunArchitectureStream); Architecture
// -> UI/UX's autoRun instead fires a plain, non-streaming mutation (runUiux.mutate({})) -- UI/UX
// Agent has no streaming backend route today, see UiuxAgentFlowContext's own docstring.
const APPROVE_CONTINUATION_BY_STAGE = {
  requirement: {
    nextAgent: "domain",
    autoRun: false,
    title: "Approve this SRS and continue to Domain Agent?",
    message: (version) =>
      `Approving v${version} makes it the SRS this feature uses going forward (any other approved SRS version is superseded back to pending). Your chat will switch to Domain Agent, where you can tell it how to enrich this SRS -- using existing domain knowledge, something specific you provide, or both.`,
  },
  domain: {
    nextAgent: "architecture",
    autoRun: true,
    title: "Approve this Enhanced SRS and start Architecture Agent?",
    message: (version) =>
      `Approving v${version} makes it the Enhanced SRS this feature uses going forward (any other approved Enhanced SRS version is superseded back to pending). Architecture Agent will start automatically and generate the Architecture Plan plus Use Case, Sequence, and Class diagrams -- watch it live in the Result panel.`,
  },
  architecture: {
    nextAgent: "uiux",
    autoRun: true,
    title: "Approve this Architecture Plan and start UI/UX Agent?",
    message: (version) =>
      `Approving v${version} makes it the Architecture Plan this feature uses going forward (any other approved Architecture Plan version is superseded back to pending). UI/UX Agent will start automatically and generate page-level UI metadata, component code, and preview screenshots -- watch it live in the Result panel.`,
  },
  // UI/UX -> Coder is the fourth link in this chain, and the first one where approving also
  // LOCKS every other pending version's Approve button (direct user request, reversing the
  // immediately-prior session's own "free approval" choice for UI/UX specifically -- see
  // UiuxVersionGroupList's own comment) -- once Coder Agent starts consuming one version as its
  // visual reference, a stray approve on a different version mid-build would be confusing and
  // could re-trigger a second, conflicting run.
  uiux: {
    nextAgent: "coder",
    autoRun: true,
    title: "Approve this UI/UX version and start Coder Agent?",
    message: (version) =>
      `Approving v${version} locks it as the UI/UX design this feature builds from -- every other version is locked from approval until you reject this one. Coder Agent will start automatically and build the real frontend + backend to match this design as closely as possible -- watch it live in the Result panel.`,
  },
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
//
// code_plan/code_diff/code_manifest/requirement_code_map are Coder Agent's own internal working
// documents -- real, useful to a human who wants to dig in, but not individually meaningful
// approval decisions the way the pipeline treats every other listed artifact. All four belong
// exclusively to the "coder" stage (per ARTIFACT_TYPE_STAGE), so excluding them by type alone,
// same mechanism as domain_improvements, needs no stage-conditional branching. The single real
// decision for this stage -- approving the generated code -- still happens exactly as before,
// through GovernancePanel's own Approve/Reject panel below (STAGE_GATING_ARTIFACT.coder points at
// code_diff/markdown, read from the unfiltered allArtifacts, independent of this list).
// use_case_diagram/sequence_diagram/class_diagram: per direct user request, diagrams no longer
// have an independent approval decision -- approving/rejecting/requesting revision on the
// Architecture Plan cascades the same decision to them automatically on the backend (see
// approval_service.py's _cascade_architecture_plan_decision). They're viewable only through
// ArchitectureDiagramsGallery now, not listed generically here.
// ui_metadata/ui_integration_manifest/ui_component_code/ui_page_html: per direct user request,
// the WHOLE UI/UX stage no longer requires any human approval decision at all -- every UI/UX
// artifact (including ui_preview_screenshot, STAGE_GATING_ARTIFACT.uiux) is saved already
// approved on the backend (see uiux_agent/agent.py's _save_artifacts). These four stay excluded
// from the listed rows for the same reason as always -- they're internal working documents, not
// individually meaningful decision points -- and ui_preview_screenshot itself still shows in
// GovernancePanel below as a plain "approved, nothing pending" status line. Raw metadata/
// manifest/component/page source is still viewable via the Preview tab and the "View" link on
// the Preview Screenshot itself where relevant -- just not as separate listed rows here.
const UNLISTED_ARTIFACT_TYPES = [
  "domain_improvements", "code_plan", "code_diff", "code_manifest", "requirement_code_map",
  "use_case_diagram", "sequence_diagram", "class_diagram",
  "ui_metadata", "ui_integration_manifest", "ui_component_code", "ui_page_html",
];

// setup_instructions is the one Coder Agent artifact still worth showing a human directly (real
// npm/build/run instructions for the generated project) -- but every past version is superseded
// the instant a newer one exists (there's nothing to compare/choose between, unlike the gating
// code_diff's own version history), so only the latest is kept.
const LATEST_VERSION_ONLY_ARTIFACT_TYPES = ["setup_instructions"];

function keepLatestVersionOnly(artifacts, types) {
  const latestVersionByType = {};
  for (const artifact of artifacts) {
    if (!types.includes(artifact.artifact_type)) continue;
    latestVersionByType[artifact.artifact_type] = Math.max(
      latestVersionByType[artifact.artifact_type] ?? 0,
      artifact.version
    );
  }
  return artifacts.filter(
    (artifact) =>
      !types.includes(artifact.artifact_type) || artifact.version === latestVersionByType[artifact.artifact_type]
  );
}

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

  // Real, confirmed bug found while building field-by-field SRS editing: this effect's own
  // comment above always claimed a new version arriving for the SAME stage would jump the
  // selector to it, but the check only ever covered "the previously-selected version vanished."
  // A freshly-created version (from a revision OR a direct field edit) never invalidates the
  // OLD version -- v2 stays a real, selectable version after v3 is created -- so `versions.some
  // (...)` still found the old selection and the effect silently did nothing, leaving a human
  // staring at their pre-edit document with no visible sign anything happened. Fixed by also
  // jumping when the latest version NUMBER has genuinely increased since the last render
  // (tracked via a ref, not `versions` itself, so an unrelated re-render -- e.g. an existing
  // version's own approval_status changing -- doesn't yank a human away from a version they're
  // deliberately reviewing).
  const previousLatestVersionRef = useRef(versions[0]?.version ?? null);
  useEffect(() => {
    const latestVersion = versions[0]?.version ?? null;
    const previousLatestVersion = previousLatestVersionRef.current;

    if (versions.length > 0 && !versions.some((v) => v.version === selectedVersion)) {
      setSelectedVersion(latestVersion);
    } else if (
      latestVersion !== null &&
      previousLatestVersion !== null &&
      latestVersion > previousLatestVersion
    ) {
      setSelectedVersion(latestVersion);
    }

    previousLatestVersionRef.current = latestVersion;
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

  // Same idea, Architecture Agent -- the plan text streams live, then a "phase" tail (use case
  // model, diagram generation, PlantUML rendering) that isn't itself streamable prose, shown via
  // LiveGenerationView's isFinalizing mode instead of a bare spinner (see that component's own
  // docstring for why). Read unconditionally regardless of stage -- cheap, and this is also what
  // handleConfirmedApprove below needs to auto-start a run from the requirement/domain branch.
  const {
    handleRunStream: handleRunArchitectureStream,
    runStream: architectureRunStream,
    runStreamedText: architectureRunStreamedText,
    runStreamStarted: architectureRunStreamStarted,
    runPhase: architectureRunPhase,
    runPhaseStartedAt: architectureRunPhaseStartedAt,
    reviseStream: architectureReviseStream,
    revisionStreamedText: architectureRevisionStreamedText,
    revisionStreamStarted: architectureRevisionStreamStarted,
    revisionPhase: architectureRevisionPhase,
    revisionPhaseStartedAt: architectureRevisionPhaseStartedAt,
  } = useArchitectureAgentFlowContext();
  const isArchitectureStage = stage === "architecture";
  const isArchitectureRevising = isArchitectureStage && architectureReviseStream.isPending;
  const isArchitectureRunning = isArchitectureStage && architectureRunStream.isPending;
  const isArchitectureGenerating = isArchitectureRevising || isArchitectureRunning;
  const architectureStreamedText = isArchitectureRevising ? architectureRevisionStreamedText : architectureRunStreamedText;
  const architectureStreamStarted = isArchitectureRevising ? architectureRevisionStreamStarted : architectureRunStreamStarted;
  const architecturePhase = isArchitectureRevising ? architectureRevisionPhase : architectureRunPhase;
  const architecturePhaseStartedAt = isArchitectureRevising ? architectureRevisionPhaseStartedAt : architectureRunPhaseStartedAt;

  // Same idea, Coder Agent -- the code plan text streams live during run()'s planning (revise()'s
  // planning uses the agentic exploration planner instead, which has no tokens at all -- see
  // CoderAgent.revise_stream's own docstring), then a "phase" tail (preparing the workspace,
  // coding attempts, verification, diffing) covers the rest, shown the same isFinalizing way
  // Architecture's diagram-generation tail already is.
  const {
    handleRunStream: handleRunCoderStream,
    runStream: coderRunStream,
    runStreamedText: coderRunStreamedText,
    runStreamStarted: coderRunStreamStarted,
    runPhase: coderRunPhase,
    runPhaseStartedAt: coderRunPhaseStartedAt,
    reviseStream: coderReviseStream,
    revisionStreamedText: coderRevisionStreamedText,
    revisionStreamStarted: coderRevisionStreamStarted,
    revisionPhase: coderRevisionPhase,
    revisionPhaseStartedAt: coderRevisionPhaseStartedAt,
  } = useCoderAgentFlowContext();
  const isCoderStage = stage === "coder";
  const isCoderRevising = isCoderStage && coderReviseStream.isPending;
  const isCoderRunning = isCoderStage && coderRunStream.isPending;
  const isCoderGenerating = isCoderRevising || isCoderRunning;
  const coderStreamedText = isCoderRevising ? coderRevisionStreamedText : coderRunStreamedText;
  const coderStreamStarted = isCoderRevising ? coderRevisionStreamStarted : coderRunStreamStarted;
  const coderPhase = isCoderRevising ? coderRevisionPhase : coderRunPhase;
  const coderPhaseStartedAt = isCoderRevising ? coderRevisionPhaseStartedAt : coderRunPhaseStartedAt;

  // Same idea, UI/UX Agent -- ui_metadata_json streams live, then a "phase" tail (component
  // generation, page assembly/rendering) covers the rest, shown the same isFinalizing way
  // Architecture/Coder's own non-streamable tails already are. Read unconditionally regardless of
  // stage -- cheap, and this is also what handleConfirmedApprove below needs to auto-start a run
  // from the architecture-approval branch.
  const {
    handleRunStream: handleRunUiuxStream,
    runStream: uiuxRunStream,
    runStreamedText: uiuxRunStreamedText,
    runStreamStarted: uiuxRunStreamStarted,
    runPhase: uiuxRunPhase,
    runPhaseStartedAt: uiuxRunPhaseStartedAt,
    reviseStream: uiuxReviseStream,
    revisionStreamedText: uiuxRevisionStreamedText,
    revisionStreamStarted: uiuxRevisionStreamStarted,
    revisionPhase: uiuxRevisionPhase,
    revisionPhaseStartedAt: uiuxRevisionPhaseStartedAt,
  } = useUiuxAgentFlowContext();
  const isUiuxStage = stage === "uiux";
  const isUiuxRevising = isUiuxStage && uiuxReviseStream.isPending;
  const isUiuxRunning = isUiuxStage && uiuxRunStream.isPending;
  const isUiuxGenerating = isUiuxRevising || isUiuxRunning;
  const uiuxStreamedText = isUiuxRevising ? uiuxRevisionStreamedText : uiuxRunStreamedText;
  const uiuxStreamStarted = isUiuxRevising ? uiuxRevisionStreamStarted : uiuxRunStreamStarted;
  const uiuxPhase = isUiuxRevising ? uiuxRevisionPhase : uiuxRunPhase;
  const uiuxPhaseStartedAt = isUiuxRevising ? uiuxRevisionPhaseStartedAt : uiuxRunPhaseStartedAt;

  // Deduped for display: every gating artifact_type saves a JSON+Markdown pair sharing one
  // version, and listing both as separate rows read as the same version being duplicated (a real
  // reported issue) -- see dedupeArtifactVersions's own docstring.
  const stageArtifacts = keepLatestVersionOnly(
    dedupeArtifactVersions(
      allArtifacts.filter(
        (a) => ARTIFACT_TYPE_STAGE[a.artifact_type] === stage && !UNLISTED_ARTIFACT_TYPES.includes(a.artifact_type)
      )
    ),
    LATEST_VERSION_ONLY_ARTIFACT_TYPES
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

  // Approving the Requirement Agent's SRS (or Domain Agent's Enhanced SRS) is where approving
  // genuinely switches the human's chat over to a different agent -- worth an explicit
  // confirmation, not just an immediate click. Owned HERE (not inside GovernancePanel or
  // ArtifactRow) because BOTH of those can offer an Approve button for a pending version now (a
  // real reported bug: only the single "operative"/highest-version artifact ever had approval
  // controls at all) -- this is their shared ancestor, and it never unmounts across the
  // approve -> switch-chat (-> auto-run) transition the way either child can (see this
  // component's own git history for the exact unmount bug this already caused once).
  //
  // Requirement -> Domain deliberately does NOT auto-run Domain Agent (it used to, immediately,
  // with an empty human_comment) -- a real, direct user report: Domain Agent already running
  // blind, before the human ever got a chance to say "use existing domain knowledge" vs. "here's
  // a database schema I want incorporated," meant their only option once they arrived at its chat
  // was to REVISE already-generated output instead of guiding the ORIGINAL generation. Approving
  // only switches the chat to Domain Agent; ChatPanel's own empty-state prompt is what invites the
  // human to guide the actual first run.
  //
  // Domain -> Architecture is the opposite, deliberately: Architecture Agent needs no comparable
  // human-guidance step (there's nothing analogous to "here's a database schema" to wait for), so
  // approving auto-starts it immediately -- see APPROVE_CONTINUATION_BY_STAGE's own `autoRun`.
  //
  // UI/UX -> Coder is the fourth link, also auto-run -- and the first stage where approving ALSO
  // locks every other pending version from being approved (UiuxVersionGroupList's own
  // `approveLocked`, computed here indirectly since this same `requestApproveConfirmation` is
  // what it calls) -- direct user request, so a stray approve on a different UI/UX version can't
  // re-trigger a second, conflicting Coder Agent run once one is already building.
  const approveContinuation = APPROVE_CONTINUATION_BY_STAGE[stage];
  const [confirmingArtifactId, setConfirmingArtifactId] = useState(null);
  // Security is a parallel special case, not another APPROVE_CONTINUATION_BY_STAGE entry -- every
  // other entry's shape is "approve -> auto-run the next agent," but approving a security report
  // needs to ask the human what to do next (proceed anyway, or send it to the Coder Agent to fix)
  // rather than silently continuing -- see SecurityDecisionDialog.jsx's own docstring for why no
  // further loop-tracking state is needed beyond this one id.
  const [securityDecisionArtifactId, setSecurityDecisionArtifactId] = useState(null);
  // Optional MongoDB URI a human can supply right in the UI/UX-approval popup (one of two new
  // entry points for this, alongside the standalone Database Connection panel reachable from
  // FeatureListPanel -- see DatabaseConnectionPanel.jsx) -- only ever read/reset for the uiux
  // stage's own dialog instance, every other stage's dialog never renders the field at all.
  const [mongoUriDraft, setMongoUriDraft] = useState("");
  const mongoUriIsValid = looksLikeMongoUri(mongoUriDraft);
  const srsApproval = useApprovalMutation(featureId);

  function requestApproveConfirmation(artifactId) {
    setMongoUriDraft("");
    setConfirmingArtifactId(artifactId);
  }

  async function handleConfirmedApprove() {
    try {
      await srsApproval.mutateAsync({ artifactId: confirmingArtifactId, status: "approved" });
    } catch {
      // Keep the dialog open -- srsApproval.error is rendered inside it so the human can see why
      // and retry or cancel, instead of the dialog vanishing on a failed approval.
      return;
    }

    setConfirmingArtifactId(null);
    selectAgent(approveContinuation.nextAgent);

    if (approveContinuation.autoRun) {
      // Not awaited: the run's own state already lives in the always-mounted flow provider (an
      // ArchitectureAgentFlowContext stream, or a UiuxAgentFlowContext mutation), so nothing is
      // lost by not waiting here -- awaiting would instead hold this dialog's "Approving..."
      // spinner up for the entire run. No pin/selection call is needed first either -- the
      // approval above just reverted every other version of this artifact_type back to pending
      // (exclusivity), so the pin-aware lookup on the backend resolves to exactly the version
      // just approved.
      if (approveContinuation.nextAgent === "architecture") {
        handleRunArchitectureStream({ use_enhanced_srs_if_available: true, architecture_notes: null, human_comment: null });
      } else if (approveContinuation.nextAgent === "uiux") {
        handleRunUiuxStream({ use_enhanced_srs_if_available: true, human_comment: null });
      } else if (approveContinuation.nextAgent === "coder") {
        // Safe by construction: run()/run_stream() (always what this fires, since UI/UX -> Coder
        // is always a FIRST run, never a revision) never short-circuit on a URI-only comment the
        // way revise() does -- passing one here saves it via the existing extract_mongodb_uri
        // call in run_stream() AND still runs the full plan/code/verify cycle using the
        // URI-stripped remainder for planning.
        handleRunCoderStream({ use_enhanced_srs_if_available: true, human_comment: mongoUriDraft.trim() || null });
      }
    }
  }

  // Security's own approve handler -- no confirmation dialog first (unlike every other gated
  // stage, there's nothing to warn about before approving; the real decision point is the popup
  // AFTER approval, not before it), just the real approval call, then open the decision popup.
  async function handleSecurityApprove(artifactId, comment) {
    await srsApproval.mutateAsync({ artifactId, status: "approved", reviewer_comment: comment ?? null });
    setSecurityDecisionArtifactId(artifactId);
  }

  // Shared by every approve-trigger surface for this stage (the "All Artifacts" list's own
  // per-row Approve button AND GovernancePanel's "Stage Actions" one) so approving from either
  // place opens the same decision popup, not just one of them.
  const onApproveClickForStage =
    stage === "security" ? handleSecurityApprove : approveContinuation ? requestApproveConfirmation : undefined;

  const confirmingArtifact = confirmingArtifactId
    ? stageArtifacts.find((a) => a.artifact_id === confirmingArtifactId)
    : null;

  // Direct user correction: a UI/UX run/revision producing several pages at once must be
  // presented (and approved) as ONE version, not as N independent-looking per-page rows -- the
  // backend already treats it that way (shared version number + approval cascade, see
  // approval_service.py's UI/UX cascade); UiuxVersionGroupList makes that true on screen too.
  // Every other stage keeps the generic ArtifactList exactly as before.
  const uiuxVersionCount = stage === "uiux" ? new Set(stageArtifacts.map((a) => a.version)).size : null;

  return (
    <div className="flex flex-col gap-5">
      {stage !== "security" && stage !== "qa" && (
      <div>
        <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">
          All Artifacts ({stage === "uiux" ? uiuxVersionCount : stageArtifacts.length})
        </h3>
        <ErrorBanner error={setActiveSelection.error} fallback="Failed to change which version is in use." />
        {stage === "uiux" ? (
          <UiuxVersionGroupList
            artifacts={stageArtifacts}
            featureId={featureId}
            onView={viewArtifact}
            onApproveClick={approveContinuation ? requestApproveConfirmation : undefined}
          />
        ) : (
          <ArtifactList
            artifacts={stageArtifacts}
            onView={viewArtifact}
            // Only used to gate the (separate, revise-only) Revise button -- approval controls are
            // no longer suppressed for any row of the gating type (see ArtifactList's docstring).
            gatingArtifactType={STAGE_GATING_ARTIFACT[stage]?.type ?? null}
            featureId={featureId}
            onApproveClick={onApproveClickForStage}
            activeArtifactType={activeArtifactType}
            activeArtifactId={effectiveActiveArtifact?.artifact_id}
            settingActive={setActiveSelection.isPending}
            onSetActive={(artifactId) =>
              setActiveSelection.mutate({ artifact_type: activeArtifactType, artifact_id: artifactId })
            }
          />
        )}
      </div>
      )}

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
      ) : isArchitectureGenerating ? (
        <LiveGenerationView
          displayText={declutterJsonForDisplay(architectureStreamedText)}
          hasStarted={architectureStreamStarted}
          connectingLabel="Connecting to Architecture Agent..."
          generatingLabel={isArchitectureRevising ? "Applying your requested change..." : "Drafting the architecture plan..."}
          isFinalizing={Boolean(architecturePhase)}
          finalizingLabel={architecturePhase?.label}
          phaseStartedAt={architecturePhaseStartedAt}
        />
      ) : isCoderGenerating ? (
        <LiveGenerationView
          displayText={declutterJsonForDisplay(coderStreamedText)}
          hasStarted={coderStreamStarted}
          connectingLabel="Connecting to Coder Agent..."
          generatingLabel={isCoderRevising ? "Applying your requested change..." : "Planning the implementation..."}
          isFinalizing={Boolean(coderPhase)}
          finalizingLabel={coderPhase?.label}
          phaseStartedAt={coderPhaseStartedAt}
        />
      ) : isUiuxGenerating ? (
        <LiveGenerationView
          displayText={declutterJsonForDisplay(uiuxStreamedText)}
          hasStarted={uiuxStreamStarted}
          connectingLabel="Connecting to UI/UX Agent..."
          generatingLabel={isUiuxRevising ? "Applying your requested change..." : "Generating ui_metadata..."}
          isFinalizing={Boolean(uiuxPhase)}
          finalizingLabel={uiuxPhase?.label}
          phaseStartedAt={uiuxPhaseStartedAt}
        />
      ) : versions.length === 0 && isRequirementStage ? (
        <RequirementSrsOutputPanel />
      ) : stage === "security" ? (
        // Unlike every other stage, Security Agent has no chat/revise flow to trigger a first
        // run from (see pipelineStages.js's MANUAL_RUN_STAGES/REVISABLE_STAGES) -- SecurityReportView
        // itself renders the "Run Security Scan" empty-state action when `artifact` is null, so
        // this branch (unlike the generic ones below) fires regardless of versions.length.
        //
        // Deliberately skips the generic "All Artifacts" full-list AND GovernancePanel further
        // down (both suppressed for this stage, see their own render guards) -- a compact version
        // dropdown plus one inline approval control replaces both, so picking a version and
        // approving/rejecting it happen in the same place instead of two differently-resolved
        // surfaces (direct user request).
        (() => {
          const selectedSecurityArtifact = versions.find((v) => v.version === selectedVersion) || versions[0] || null;
          const securityApproveLocked = selectedSecurityArtifact
            ? Boolean(
                stageArtifacts.find(
                  (a) =>
                    a.artifact_type === "security_report" &&
                    a.approval_status === "approved" &&
                    a.artifact_id !== selectedSecurityArtifact.artifact_id
                )
              )
            : false;

          return (
            <div className="flex flex-col gap-4">
              {versions.length > 0 && (
                <div className="flex items-center justify-between">
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
                  {selectedSecurityArtifact && (
                    <a
                      href={artifactDownloadUrl(selectedSecurityArtifact.artifact_id)}
                      className="text-sm text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300 font-semibold"
                    >
                      Download report
                    </a>
                  )}
                </div>
              )}

              {selectedSecurityArtifact &&
                (selectedSecurityArtifact.approval_status === "pending" ? (
                  <ApprovalPanel
                    featureId={featureId}
                    artifact={selectedSecurityArtifact}
                    approveLocked={securityApproveLocked}
                    onApproveClick={(comment) => handleSecurityApprove(selectedSecurityArtifact.artifact_id, comment)}
                  />
                ) : (
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    v{selectedSecurityArtifact.version} is {selectedSecurityArtifact.approval_status}.
                  </p>
                ))}

              <SecurityReportView artifact={selectedSecurityArtifact} featureId={featureId} />
            </div>
          );
        })()
      ) : stage === "qa" ? (
        // Same reasoning as the security branch above, minus the approval popup entirely -- QA
        // stays auto-approved (see pipelineStages.js's AUTO_APPROVED_STAGES), so there's no
        // pending/approved distinction to render here, just the version dropdown plus
        // QaReportView (which owns its own "Re-run" / "Send Failing Tests to Coder Agent" actions).
        // Also fires the "Run QA Scan" empty state itself when `artifact` is null, same as
        // SecurityReportView, so this branch fires regardless of versions.length too.
        (() => {
          const selectedQaArtifact = versions.find((v) => v.version === selectedVersion) || versions[0] || null;
          return (
            <div className="flex flex-col gap-4">
              {versions.length > 0 && (
                <div className="flex items-center justify-between">
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
                  {selectedQaArtifact && (
                    <a
                      href={artifactDownloadUrl(selectedQaArtifact.artifact_id)}
                      className="text-sm text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300 font-semibold"
                    >
                      Download report
                    </a>
                  )}
                </div>
              )}

              <QaReportView artifact={selectedQaArtifact} featureId={featureId} />
            </div>
          );
        })()
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
                  <ArtifactContentView
                    artifact={artifact}
                    domainImprovementsArtifact={domainImprovements}
                  />
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

      {stage !== "security" && stage !== "qa" && (
      <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
        <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">Governance</h3>
        <GovernancePanel
          stage={stage}
          featureId={featureId}
          allArtifacts={allArtifacts}
          stageArtifacts={stageArtifacts}
          onApproveClick={onApproveClickForStage}
        />
      </div>
      )}

      {approveContinuation && (
        <ConfirmDialog
          open={Boolean(confirmingArtifactId)}
          onClose={() => {
            if (!srsApproval.isPending) {
              setConfirmingArtifactId(null);
              setMongoUriDraft("");
            }
          }}
          onConfirm={handleConfirmedApprove}
          title={approveContinuation.title}
          message={approveContinuation.message(confirmingArtifact?.version)}
          confirmLabel="Approve & Continue"
          confirmingLabel="Approving..."
          tone="primary"
          confirming={srsApproval.isPending}
          confirmDisabled={stage === "uiux" && mongoUriDraft.trim().length > 0 && !mongoUriIsValid}
          error={srsApproval.error}
          errorFallback="Failed to submit approval decision."
        >
          {stage === "uiux" && (
            <div>
              <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                MongoDB connection string (optional)
              </label>
              <input
                type="text"
                value={mongoUriDraft}
                onChange={(e) => setMongoUriDraft(e.target.value)}
                placeholder="mongodb+srv://user:password@cluster0.xxx.mongodb.net/mydb"
                className="w-full px-3 py-2 text-sm font-mono border border-gray-300 dark:border-gray-600 dark:bg-white/5 dark:text-gray-100 rounded-md focus:outline-none focus:border-accent-500"
              />
              {mongoUriDraft.trim().length > 0 && !mongoUriIsValid && (
                <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                  Must start with mongodb:// or mongodb+srv://
                </p>
              )}
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                Leave blank to keep serving seed data, or add/change it later from the Database
                Connection panel.
              </p>
            </div>
          )}
        </ConfirmDialog>
      )}

      <SecurityDecisionDialog
        artifactId={securityDecisionArtifactId}
        featureId={featureId}
        onClose={() => setSecurityDecisionArtifactId(null)}
      />
    </div>
  );
}
