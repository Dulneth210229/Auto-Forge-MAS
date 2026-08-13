import { useState } from "react";
import { useUiuxAgentFlowContext } from "../workspace/UiuxAgentFlowContext";
import { listGatingArtifactVersions } from "../../lib/deriveStageStatus";
import { SUGGESTION_CHIPS } from "../../lib/suggestionChips";
import { LiveReactionBubble, useElapsedLabel } from "../pipeline/RequirementConversationParts";
import ChatBubble from "./ChatBubble";
import ChatComposerBox from "./ChatComposerBox";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorBanner from "../common/ErrorBanner";

function ChatHeader({ feature, runningStage }) {
  return (
    <div className="flex items-center justify-between gap-2 flex-shrink-0 pb-3 border-b border-gray-100 dark:border-gray-800">
      <div className="min-w-0">
        <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 truncate">{feature?.feature_name || "..."}</h2>
        <p className="text-xs text-gray-400 dark:text-gray-500 truncate">{feature?.feature_description}</p>
      </div>
      {runningStage && (
        <div className="flex items-center gap-1.5 bg-accent-50 dark:bg-accent-500/10 text-accent-700 dark:text-accent-300 text-xs font-semibold rounded-full px-2.5 py-1 flex-shrink-0">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-500" />
          </span>
          Agent running
        </div>
      )}
    </div>
  );
}

// UI/UX Agent's own dedicated chat, mirroring ArchitectureAgentChat.jsx -- live token-by-token
// ui_metadata_json streaming, a phase/elapsed-time banner for the non-streamable tail (component
// generation, page assembly/rendering), composer clears and an optimistic bubble appears
// immediately on submit, a Stop button while a stream is in flight. Direct user request: UI/UX
// Agent previously had NO revise capability at all (only a one-shot /uiux/run, no way to change
// already-generated output by messaging the agent) and its output required human approval on
// every artifact -- both fixed on the backend (uiux_agent.py's revise()/revise_stream(), and
// every UI/UX artifact now saves already approved) -- this component is the "chat, just like the
// other agents" half of that same request. No "/" document-mention picker (Domain-specific) and
// no "deep exploration mode" escape hatch (Architecture-specific) -- UI/UX Agent has neither
// concept.
export default function UiuxAgentChat({
  featureId,
  feature,
  runningStage,
  selectedAgent,
  selectAgent,
  timeline,
  allArtifacts,
  onViewArtifact,
  isLoadingTimeline,
}) {
  const {
    runStream,
    handleRunStream,
    stopRunStream,
    runStreamStarted,
    runPhase,
    runPhaseStartedAt,
    runStreamError,
    reviseStream,
    handleReviseStream,
    stopReviseStream,
    revisionStreamStarted,
    revisionPhase,
    revisionPhaseStartedAt,
    revisionStreamError,
  } = useUiuxAgentFlowContext();

  const [comment, setComment] = useState("");
  const [pendingHumanReply, setPendingHumanReply] = useState(null);

  const versions = listGatingArtifactVersions("uiux", allArtifacts);
  const hasOutput = versions.length > 0;

  const activeStream = hasOutput ? reviseStream : runStream;
  const streamStarted = hasOutput ? revisionStreamStarted : runStreamStarted;
  const stopActiveStream = hasOutput ? stopReviseStream : stopRunStream;
  // Set from a real {"type": "error"} NDJSON line -- unlike activeStream.error (only set on a
  // genuine promise rejection), this is the only signal available when the stream completed
  // "successfully" from fetch's point of view but the agent itself crashed mid-attempt.
  const streamError = hasOutput ? revisionStreamError : runStreamError;
  const activePhase = hasOutput ? revisionPhase : runPhase;
  const activePhaseStartedAt = hasOutput ? revisionPhaseStartedAt : runPhaseStartedAt;

  // Shared by the composer's Send and a chat bubble's inline "Save & Send" -- both ultimately
  // fire the same stream (run vs. revise) with whatever text the human settled on. The human's
  // message appears in the chat feed immediately via pendingHumanReply -- the real "ask" bubble
  // only lands once the invalidated events query refetches (see useUiuxAgentFlow.js's own comment
  // on why that refetch MUST be awaited).
  function submitUiuxMessage(text) {
    if (activeStream.isPending) return;
    const trimmed = text.trim();

    setPendingHumanReply(trimmed);

    const call = hasOutput
      ? handleReviseStream({ revision_comment: trimmed, revised_by: "human_user" })
      : handleRunStream({ use_enhanced_srs_if_available: true, human_comment: trimmed });

    call.finally(() => setPendingHumanReply(null));
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (activeStream.isPending) return;
    const trimmed = comment.trim();
    if (!trimmed) return;

    setComment("");
    submitUiuxMessage(trimmed);
  }

  // The primary way UI/UX Agent's first run actually starts is the auto-continue flow from
  // approving an Architecture Plan (ResultTab.jsx), which calls handleRunStream directly and
  // never touches this chat at all. This button exists for the secondary path -- a human who
  // navigates here directly -- since the composer otherwise requires non-empty text to submit.
  function handleStartWithoutNotes() {
    if (activeStream.isPending) return;
    submitUiuxMessage("");
  }

  const isAgentRunning = runningStage === "uiux" || activeStream.isPending;
  // Real ticking timer, not a static render-time-only label -- ui_metadata_json streams very
  // quickly, so most of a run's real wall-clock time is spent in the non-streamable
  // component-generation/assembly tail, which otherwise reads as stuck with no live text moving.
  const elapsedLabel = useElapsedLabel(activePhaseStartedAt);

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-4">
      <ChatHeader feature={feature} runningStage={runningStage} />

      <div className="flex-1 min-h-0 overflow-y-auto py-3 flex flex-col gap-3">
        {isLoadingTimeline ? (
          <LoadingSpinner label="Loading activity..." />
        ) : timeline.length === 0 && pendingHumanReply === null && !activeStream.isPending ? (
          <p className="text-sm text-gray-400 dark:text-gray-500 italic">No activity yet. Say something below to get started.</p>
        ) : (
          timeline.map((item, i) => (
            <ChatBubble
              key={i}
              item={item}
              allArtifacts={allArtifacts}
              onViewArtifact={onViewArtifact}
              onEditSubmit={(text) => submitUiuxMessage(text)}
              isEditPending={activeStream.isPending}
            />
          ))
        )}

        {pendingHumanReply !== null && (
          <div className="flex justify-end">
            <div className="max-w-[85%] bg-accent-600 dark:bg-accent-500 text-white rounded-lg rounded-tr-sm px-3 py-2 text-sm">
              <p className="text-xs text-accent-200 dark:text-accent-100/80 mb-0.5">You</p>
              <p className="whitespace-pre-wrap">
                {pendingHumanReply || (
                  <span className="italic text-accent-200 dark:text-accent-100/80">(no comment provided)</span>
                )}
              </p>
            </div>
          </div>
        )}

        {activeStream.isPending && (
          <>
            <LiveReactionBubble reactionText={null} hasStarted={streamStarted} agentLabel="UI/UX Agent" />
            {streamStarted && (
              <div className="flex items-center justify-between gap-2 bg-accent-50 dark:bg-accent-500/10 border border-accent-200 dark:border-accent-500/30 rounded-lg px-3 py-2.5">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="relative flex h-2 w-2 flex-shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-600" />
                  </span>
                  <p className="text-sm text-accent-800 dark:text-accent-300 font-semibold truncate">
                    {activePhase
                      ? `${activePhase.label}${elapsedLabel ? ` · ${elapsedLabel}` : ""}`
                      : `${hasOutput ? "Applying your requested change" : "Generating pages, components, and previews"} -- watch progress live in the Result panel →`}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={stopActiveStream}
                  className="text-xs font-semibold text-accent-700 dark:text-accent-300 hover:text-accent-900 dark:hover:text-accent-100 underline flex-shrink-0"
                >
                  Stop
                </button>
              </div>
            )}
          </>
        )}

        <ErrorBanner
          error={activeStream.error || (streamError && { message: streamError })}
          fallback="UI/UX Agent request failed."
        />
      </div>

      <div className="flex-shrink-0 pt-1">
        {!hasOutput && !activeStream.isPending && (
          <button
            type="button"
            onClick={handleStartWithoutNotes}
            className="mb-2 self-start text-xs font-semibold bg-white dark:bg-white/10 hover:bg-accent-100 dark:hover:bg-white/20 text-accent-700 dark:text-accent-300 border border-accent-300 dark:border-accent-500/40 rounded-full px-3 py-1"
          >
            Start UI/UX Agent now
          </button>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          {SUGGESTION_CHIPS.uiux && (
            <div className="flex flex-wrap gap-1.5">
              {SUGGESTION_CHIPS.uiux.map((chip) => (
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
            onChange={(event) => setComment(event.target.value)}
            disabled={false}
            pending={activeStream.isPending}
            onStop={stopActiveStream}
            selectedAgent={selectedAgent}
            onSelectAgent={selectAgent}
            isAgentRunning={isAgentRunning}
            placeholder={
              hasOutput ? "Ask UI/UX Agent for a change..." : "Tell UI/UX Agent what to build (optional)..."
            }
          />
        </form>
      </div>
    </div>
  );
}
