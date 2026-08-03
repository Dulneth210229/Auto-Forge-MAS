import { useEffect, useRef, useState } from "react";
import { useFeature } from "../../hooks/useFeatures";
import { useFeatureApprovals, useFeatureEvents, useGraphStatus } from "../../hooks/usePipeline";
import { useFeatureArtifacts } from "../../hooks/useArtifacts";
import { useKnowledgeDocuments } from "../../hooks/useKnowledgeDocuments";
import { deriveStageStatus, listGatingArtifactVersions, STATUS } from "../../lib/deriveStageStatus";
import { GATED_STAGES, STAGE_LABELS } from "../../lib/pipelineStages";
import { buildAgentTimeline } from "../../lib/buildAgentTimeline";
import { SUGGESTION_CHIPS } from "../../lib/suggestionChips";
import { useWorkspaceSelection } from "../workspace/WorkspaceSelectionContext";
import {
  useReviseArchitecture,
  useReviseCoder,
  useReviseDomain,
  useRunArchitecture,
  useRunCoder,
  useRunDomain,
  useRunUiux,
} from "../../hooks/useAgentMutations";
import ArchitectureRunForm from "../pipeline/ArchitectureRunForm";
import ChatBubble from "./ChatBubble";
import ChatComposerBox from "./ChatComposerBox";
import DocumentMentionPicker from "./DocumentMentionPicker";
import RequirementConversationChat from "./RequirementConversationChat";
import RequirementRevisionChat from "./RequirementRevisionChat";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorBanner from "../common/ErrorBanner";

// Matches a trailing "/word" token at the end of the text typed so far (e.g. "check the /sche"
// while typing "/schema.pdf") -- used to open the document mention picker. Requires the "/" to
// start a token (start-of-string or preceded by whitespace) so a literal "/" inside a normal
// sentence (e.g. "input/output") doesn't spuriously trigger it.
const MENTION_TRIGGER_PATTERN = /(?:^|\s)\/(\w*)$/;

function isProcessingNode(graphStatus, stage) {
  return Boolean(graphStatus?.next?.includes(`${stage}_node`));
}

// "System must render what agent is currently running" -- independent of which agent the user
// has selected to chat with, this surfaces whichever auto-run stage the LangGraph pipeline is
// actively executing right now (domain/uiux/coder are the only stages that ever run unattended).
function RunningBadge({ runningStage }) {
  if (!runningStage) return null;
  return (
    <div className="flex items-center gap-1.5 bg-accent-50 dark:bg-accent-500/10 text-accent-700 dark:text-accent-300 text-xs font-semibold rounded-full px-2.5 py-1 flex-shrink-0">
      <span className="relative flex h-1.5 w-1.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-500" />
      </span>
      {STAGE_LABELS[runningStage]} Agent running
    </div>
  );
}

function ChatHeader({ feature, runningStage }) {
  return (
    <div className="flex items-center justify-between gap-2 flex-shrink-0 pb-3 border-b border-gray-100 dark:border-gray-800">
      <div className="min-w-0">
        <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 truncate">{feature?.feature_name || "..."}</h2>
        <p className="text-xs text-gray-400 dark:text-gray-500 truncate">{feature?.feature_description}</p>
      </div>
      <RunningBadge runningStage={runningStage} />
    </div>
  );
}

export default function ChatPanel({ featureId }) {
  const { selectedAgent, selectAgent, viewArtifact } = useWorkspaceSelection();
  const { data: feature } = useFeature(featureId);
  const { data: graphStatus, isLoading: graphLoading } = useGraphStatus(featureId);

  const runningStage = ["domain", "uiux", "coder"].find((stage) => isProcessingNode(graphStatus, stage));
  const anyProcessing = Boolean(runningStage);
  const { data: artifacts, isLoading: artifactsLoading, error: artifactsError } = useFeatureArtifacts(featureId, {
    isProcessing: anyProcessing,
  });
  const { data: approvals } = useFeatureApprovals(featureId);
  const { data: events, isLoading: eventsLoading } = useFeatureEvents(featureId);

  // Same stuck-detection idiom the old FeatureDetailPage used -- tracks how long each auto-run
  // stage has been "processing" so a genuinely stuck run can be distinguished from a normal wait.
  const processingSinceRef = useRef({});
  useEffect(() => {
    if (!graphStatus) return;
    for (const stage of ["domain", "uiux", "coder"]) {
      if (isProcessingNode(graphStatus, stage)) {
        if (!processingSinceRef.current[stage]) processingSinceRef.current[stage] = Date.now();
      } else {
        processingSinceRef.current[stage] = null;
      }
    }
  }, [graphStatus]);

  const allArtifacts = artifacts || [];
  const allApprovals = approvals || [];
  const allEvents = events || [];

  const stageStatuses = {};
  for (const stage of GATED_STAGES) {
    stageStatuses[stage] = deriveStageStatus({
      stage,
      graphStatus,
      artifacts: allArtifacts,
      processingSince: processingSinceRef.current[stage],
      now: Date.now(),
    });
  }

  // Not memoized: allArtifacts/allApprovals/allEvents are fresh `|| []` fallbacks each render
  // (see above), so a dependency array here would never actually skip recomputation anyway --
  // buildAgentTimeline itself is cheap (a handful of array scans + one sort).
  const timeline = buildAgentTimeline(allArtifacts, allApprovals, allEvents);

  const [comment, setComment] = useState("");
  const [showArchitectureForm, setShowArchitectureForm] = useState(false);

  // "/" document mention (Domain Agent only) -- referencedDocuments holds the picked
  // {document_id, original_filename} chips; mentionQuery is non-null while the picker is open,
  // holding whatever's been typed after "/" so far.
  const [referencedDocuments, setReferencedDocuments] = useState([]);
  const [mentionQuery, setMentionQuery] = useState(null);

  const projectId = feature?.project_id;
  const isDomainSelected = selectedAgent === "domain";
  const { data: knowledgeDocuments } = useKnowledgeDocuments(projectId, {
    enabled: Boolean(projectId) && isDomainSelected,
  });

  const runArchitecture = useRunArchitecture(featureId);
  const runUiux = useRunUiux(featureId);
  const runCoder = useRunCoder(featureId);
  const runDomain = useRunDomain(featureId);
  const reviseDomain = useReviseDomain(featureId);
  const reviseArchitecture = useReviseArchitecture(featureId);
  const reviseCoder = useReviseCoder(featureId);

  const runMutationsByStage = { architecture: runArchitecture, uiux: runUiux, coder: runCoder, domain: runDomain };
  const reviseMutationsByStage = {
    domain: reviseDomain,
    architecture: reviseArchitecture,
    coder: reviseCoder,
  };

  function handleCommentChange(event) {
    const value = event.target.value;
    setComment(value);

    if (!isDomainSelected) {
      setMentionQuery(null);
      return;
    }

    const match = value.slice(0, event.target.selectionStart ?? value.length).match(MENTION_TRIGGER_PATTERN);
    setMentionQuery(match ? match[1] : null);
  }

  function handleMentionSelect(doc) {
    setComment((current) => current.replace(MENTION_TRIGGER_PATTERN, (full) => (full.startsWith(" ") ? " " : "")));
    setReferencedDocuments((current) =>
      current.some((d) => d.document_id === doc.document_id) ? current : [...current, doc]
    );
    setMentionQuery(null);
  }

  function removeReferencedDocument(documentId) {
    setReferencedDocuments((current) => current.filter((d) => d.document_id !== documentId));
  }

  const versions = listGatingArtifactVersions(selectedAgent, allArtifacts);
  const hasOutput = versions.length > 0;

  // Requirement Agent, pre-SRS: built from the exact same building blocks as every other agent's
  // chat (ChatHeader, ChatComposerBox) instead of a separate bespoke UI -- per direct user
  // feedback that the chat window must look and behave the same regardless of which agent is
  // selected. Only the data source (a conversation's turn_history, not the generic cross-agent
  // timeline) and what Send does (reply to the conversation, not run/revise) differ.
  if (selectedAgent === "requirement" && !hasOutput) {
    return (
      <RequirementConversationChat
        featureId={featureId}
        feature={feature}
        runningStage={runningStage}
        selectedAgent={selectedAgent}
        selectAgent={selectAgent}
      />
    );
  }

  // Requirement Agent, post-SRS: same reasoning as the pre-SRS branch above, but for asking the
  // already-generated SRS to change -- live, streamed revision instead of the generic ChatPanel
  // composer's blocking-wait-then-static-reveal (see RequirementRevisionChat's own docstring).
  if (selectedAgent === "requirement" && hasOutput) {
    return (
      <RequirementRevisionChat
        featureId={featureId}
        feature={feature}
        runningStage={runningStage}
        selectedAgent={selectedAgent}
        selectAgent={selectAgent}
        timeline={timeline}
        allArtifacts={allArtifacts}
        onViewArtifact={viewArtifact}
        isLoadingTimeline={graphLoading || artifactsLoading || eventsLoading}
      />
    );
  }

  const runMutation = runMutationsByStage[selectedAgent];
  const reviseMutation = reviseMutationsByStage[selectedAgent];
  const activeMutation = hasOutput ? reviseMutation : runMutation;
  const isAgentRunning = runningStage === selectedAgent || Boolean(activeMutation?.isPending);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!comment.trim() || !activeMutation) return;

    const referencedDocumentIds = referencedDocuments.map((doc) => doc.document_id);

    if (hasOutput) {
      await activeMutation.mutateAsync({
        revision_comment: comment.trim(),
        revised_by: "human_user",
        ...(isDomainSelected ? { referenced_document_ids: referencedDocumentIds } : {}),
      });
    } else if (selectedAgent === "architecture") {
      await activeMutation.mutateAsync({ human_comment: comment.trim(), architecture_notes: null });
    } else {
      await activeMutation.mutateAsync({
        human_comment: comment.trim(),
        ...(isDomainSelected ? { referenced_document_ids: referencedDocumentIds } : {}),
      });
    }
    setComment("");
    setReferencedDocuments([]);
    setMentionQuery(null);
  }

  const status = stageStatuses[selectedAgent];
  const canCompose = hasOutput ? Boolean(reviseMutation) : Boolean(runMutation);

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-4">
      <ChatHeader feature={feature} runningStage={runningStage} />

      <ErrorBanner error={artifactsError} fallback="Failed to load artifacts." />

      <div className="flex-1 min-h-0 overflow-y-auto py-3 flex flex-col gap-3">
        {graphLoading || artifactsLoading || eventsLoading ? (
          <LoadingSpinner label="Loading activity..." />
        ) : timeline.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-500 italic">No activity yet. Say something below to get started.</p>
        ) : (
          timeline.map((item, i) => (
            <ChatBubble key={i} item={item} allArtifacts={allArtifacts} onViewArtifact={viewArtifact} onEdit={setComment} />
          ))
        )}

        {status === STATUS.PROCESSING && (
          <LoadingSpinner label={`${STAGE_LABELS[selectedAgent]} Agent is working...`} />
        )}

        {status === STATUS.POSSIBLY_STUCK && (
          <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg p-3">
            <p className="text-sm font-semibold text-red-800 dark:text-red-300">Taking longer than expected.</p>
            <p className="text-xs text-red-700 dark:text-red-400 mt-1">
              Still polling automatically -- if the underlying issue resolves, this will pick up the
              result without a refresh.
            </p>
          </div>
        )}
      </div>

      <div className="flex-shrink-0 pt-1">
        {!hasOutput && selectedAgent === "domain" && (
          <div className="bg-accent-50 dark:bg-accent-500/10 border border-accent-200 dark:border-accent-500/30 rounded-md px-3 py-2.5 mb-2">
            <p className="text-sm font-semibold text-accent-900 dark:text-accent-200">
              Should Domain Agent enrich this SRS using its existing domain knowledge, or do you
              have something specific to add -- like a database schema, a compliance rule, or a
              business constraint?
            </p>
            <p className="text-xs text-accent-700 dark:text-accent-400 mt-1">
              Describe it below, or type <code>/</code> to reference an uploaded document. If you
              don't have anything specific, just click through and it'll use domain knowledge
              alone.
            </p>
            <button
              type="button"
              onClick={() => runDomain.mutate({})}
              disabled={runDomain.isPending}
              className="mt-2 text-xs font-semibold bg-white dark:bg-white/10 hover:bg-accent-100 dark:hover:bg-white/20 disabled:opacity-50 text-accent-700 dark:text-accent-300 border border-accent-300 dark:border-accent-500/40 rounded-full px-3 py-1"
            >
              {runDomain.isPending ? "Starting..." : "Just use domain knowledge"}
            </button>
            <ErrorBanner error={runDomain.error} fallback="Failed to start Domain Agent." />
          </div>
        )}

        {hasOutput && selectedAgent === "uiux" && (
          <p className="text-xs bg-gray-50 dark:bg-white/5 text-gray-500 dark:text-gray-400 rounded-md px-2.5 py-1.5 mb-2">
            There's no revise action for UI/UX yet -- approve, reject, or request revision on
            individual components from the Result tab.
          </p>
        )}

        {!hasOutput && selectedAgent === "architecture" && (
          <div className="mb-2">
            <button
              type="button"
              onClick={() => setShowArchitectureForm((v) => !v)}
              className="text-xs text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300 font-semibold underline"
            >
              {showArchitectureForm ? "Use the quick chat box instead" : "Prefer a detailed form instead?"}
            </button>
            {showArchitectureForm && (
              <div className="mt-2">
                <ArchitectureRunForm featureId={featureId} />
              </div>
            )}
          </div>
        )}

        {!(selectedAgent === "architecture" && !hasOutput && showArchitectureForm) && (
          <form onSubmit={handleSubmit} className="flex flex-col gap-2">
            <ErrorBanner error={activeMutation?.error} fallback="Request failed." />

            {canCompose && SUGGESTION_CHIPS[selectedAgent] && (
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTION_CHIPS[selectedAgent].map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => setComment(chip)}
                    className="text-xs bg-gray-100 dark:bg-white/10 hover:bg-gray-200 dark:hover:bg-white/20 text-gray-700 dark:text-gray-300 rounded-full px-2.5 py-1"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            )}

            <ChatComposerBox
              value={comment}
              onChange={handleCommentChange}
              disabled={!canCompose}
              pending={activeMutation?.isPending}
              selectedAgent={selectedAgent}
              onSelectAgent={selectAgent}
              isAgentRunning={isAgentRunning}
              placeholder={
                !canCompose
                  ? `${STAGE_LABELS[selectedAgent]} Agent can't be messaged directly right now`
                  : hasOutput
                  ? `Ask ${STAGE_LABELS[selectedAgent]} Agent for a change...`
                  : isDomainSelected
                  ? "e.g. Here's our database schema: ... (or leave blank and use the button above)"
                  : `Tell ${STAGE_LABELS[selectedAgent]} Agent what to build...`
              }
            >
              {mentionQuery !== null && (
                <DocumentMentionPicker
                  documents={knowledgeDocuments}
                  query={mentionQuery}
                  onSelect={handleMentionSelect}
                />
              )}

              {isDomainSelected && referencedDocuments.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {referencedDocuments.map((doc) => (
                    <span
                      key={doc.document_id}
                      className="inline-flex items-center gap-1 text-xs bg-accent-50 dark:bg-accent-500/15 text-accent-700 dark:text-accent-300 rounded-full px-2 py-1"
                    >
                      {doc.original_filename}
                      <button
                        type="button"
                        onClick={() => removeReferencedDocument(doc.document_id)}
                        className="text-accent-500 hover:text-accent-800 dark:hover:text-accent-100"
                        aria-label={`Remove ${doc.original_filename}`}
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </ChatComposerBox>
          </form>
        )}
      </div>
    </div>
  );
}
