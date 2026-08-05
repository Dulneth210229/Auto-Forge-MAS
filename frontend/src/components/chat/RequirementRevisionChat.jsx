import { useState } from "react";
import { useRequirementConversationFlowContext } from "../workspace/RequirementConversationFlowContext";
import { LiveReactionBubble } from "../pipeline/RequirementConversationParts";
import { extractStreamingJsonStringField } from "../../lib/streamingJsonDisplay";
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

// Requirement Agent, POST-SRS: asking for a change here used to be a blocking wait (the generic
// ChatPanel composer, calling the plain non-streaming /requirement/revise) followed by a static
// "Produced SRS (vN)" bubble appearing out of nowhere once it finished -- per direct user
// feedback, the second (and every later) SRS revision needs the exact same live, ChatGPT/Claude-
// style experience the FIRST generation already has. Built from the same building blocks as
// RequirementConversationChat (pre-SRS): the human's message appears immediately, the agent's
// revision_summary reaction streams in as a real chat bubble (no JSON), and the regenerated
// document itself streams in the Result panel -- see RequirementSrsOutputPanel's sibling handling
// in ResultTab for that half.
export default function RequirementRevisionChat({
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
  const { reviseStream, handleReviseStream, stopReviseStream, revisionStreamedText, revisionStreamStarted } =
    useRequirementConversationFlowContext();

  const [comment, setComment] = useState("");
  const [pendingHumanReply, setPendingHumanReply] = useState(null);

  // Shared by the composer's Send and a chat bubble's inline "Save & Send" (see ChatBubble's own
  // docstring for why editing an old ask bubble resubmits rather than rewriting history).
  function submitRevision(text) {
    if (reviseStream.isPending) return;
    const trimmed = text.trim();
    if (!trimmed) return;

    setPendingHumanReply(trimmed);
    handleReviseStream({ revision_comment: trimmed, revised_by: "human_user" }).finally(() =>
      setPendingHumanReply(null)
    );
  }

  function handleSubmit(event) {
    event.preventDefault();
    const trimmed = comment.trim();
    if (!trimmed) return;
    setComment("");
    submitRevision(trimmed);
  }

  const reactionText = extractStreamingJsonStringField(revisionStreamedText, "revision_summary");

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-4">
      <ChatHeader feature={feature} runningStage={runningStage} />

      <div className="flex-1 min-h-0 overflow-y-auto py-3 flex flex-col gap-3">
        {isLoadingTimeline ? (
          <LoadingSpinner label="Loading activity..." />
        ) : timeline.length === 0 && !pendingHumanReply ? (
          <p className="text-sm text-gray-400 dark:text-gray-500 italic">No activity yet. Say something below to get started.</p>
        ) : (
          timeline.map((item, i) => (
            <ChatBubble
              key={i}
              item={item}
              allArtifacts={allArtifacts}
              onViewArtifact={onViewArtifact}
              onEditSubmit={submitRevision}
              isEditPending={reviseStream.isPending}
            />
          ))
        )}

        {pendingHumanReply && (
          <div className="flex justify-end">
            <div className="max-w-[85%] bg-accent-600 dark:bg-accent-500 text-white rounded-lg rounded-tr-sm px-3 py-2 text-sm">
              <p className="text-xs text-accent-200 dark:text-accent-100/80 mb-0.5">You</p>
              <p className="whitespace-pre-wrap">{pendingHumanReply}</p>
            </div>
          </div>
        )}

        {reviseStream.isPending && (
          <>
            <LiveReactionBubble reactionText={reactionText} hasStarted={revisionStreamStarted} />
            {revisionStreamStarted && (
              <div className="flex items-center justify-between gap-2 bg-accent-50 dark:bg-accent-500/10 border border-accent-200 dark:border-accent-500/30 rounded-lg px-3 py-2.5">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="relative flex h-2 w-2 flex-shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-600" />
                  </span>
                  <p className="text-sm text-accent-800 dark:text-accent-300 font-semibold truncate">
                    Applying your requested change -- watch progress live in the Result panel &rarr;
                  </p>
                </div>
                <button
                  type="button"
                  onClick={stopReviseStream}
                  className="text-xs font-semibold text-accent-700 dark:text-accent-300 hover:text-accent-900 dark:hover:text-accent-100 underline flex-shrink-0"
                >
                  Stop
                </button>
              </div>
            )}
          </>
        )}

        <ErrorBanner error={reviseStream.error} fallback="Failed to revise the SRS." />
      </div>

      <div className="flex-shrink-0 pt-1">
        <form onSubmit={handleSubmit}>
          <ChatComposerBox
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            disabled={reviseStream.isPending}
            pending={reviseStream.isPending}
            onStop={stopReviseStream}
            selectedAgent={selectedAgent}
            onSelectAgent={selectAgent}
            isAgentRunning={runningStage === "requirement" || reviseStream.isPending}
            placeholder="Ask Requirement Agent for a change..."
          />
        </form>
      </div>
    </div>
  );
}
