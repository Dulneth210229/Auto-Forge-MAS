import { useState } from "react";
import { useRequirementConversationFlowContext } from "../workspace/RequirementConversationFlowContext";
import { AgentTurnBubble, HumanBubble, LiveReactionBubble, QualityGateBanner } from "../pipeline/RequirementConversationParts";
import RequirementRunForm from "../pipeline/RequirementRunForm";
import ChatComposerBox from "./ChatComposerBox";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorBanner from "../common/ErrorBanner";
import { extractStreamingJsonStringField } from "../../lib/streamingJsonDisplay";

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

// The Requirement Agent's pre-SRS conversational gap-filling flow, wrapped in the exact same
// shell (header + scrollable message area + ChatComposerBox) every other agent's chat uses --
// per direct user feedback that the chat window must be visually/behaviorally consistent across
// agents. Replies go through one free-text box (like every other agent), not a stack of
// per-question inputs; the questions' example answers are shown inline in AgentTurnBubble instead.
export default function RequirementConversationChat({ featureId, feature, runningStage, selectedAgent, selectAgent }) {
  const {
    conversation,
    isLoading,
    start,
    respondStream,
    handleReplyStream,
    stopReplyStream,
    replyStreamedText,
    replyStreamStarted,
    respondWithDocument,
    editTurnStream,
    handleEditTurnStream,
    stopEditTurnStream,
    editStreamedText,
    editStreamStarted,
    reset,
    confirmStream,
    handleConfirm,
    stopConfirmStream,
    isGenerating,
    isConfirmed,
  } = useRequirementConversationFlowContext();

  const [replyText, setReplyText] = useState("");
  const [attachedFile, setAttachedFile] = useState(null);
  const [showManualForm, setShowManualForm] = useState(false);
  // The reply is optimistically shown as a real chat bubble the instant it's sent -- the actual
  // turn (with the agent's reaction+questions) only lands in conversation.turn_history once the
  // whole stream finishes, and without this the human's own message would appear to vanish for
  // however long generation takes.
  const [pendingHumanReply, setPendingHumanReply] = useState(null);
  // Same idea for an edited-and-resent turn: { turnIndex, pendingReply } while a streamed
  // regeneration from that turn is in flight, else null. Editing discards this turn and every
  // turn after it (see editTurnStream's own docstring), so while this is set, later turns are
  // hidden entirely rather than briefly shown then yanked away once the stream finishes.
  const [editingContext, setEditingContext] = useState(null);

  function handleEditTurn(turnIndex, newReply) {
    setEditingContext({ turnIndex, pendingReply: newReply });
    handleEditTurnStream({ turnIndex, reply: newReply }).finally(() => setEditingContext(null));
  }

  const isReplying = respondStream.isPending || respondWithDocument.isPending;

  function handleReplySubmit(event) {
    event.preventDefault();
    if (isReplying) return;
    const trimmed = replyText.trim();
    if (!trimmed && !attachedFile) return;

    setReplyText("");
    setAttachedFile(null);

    if (attachedFile) {
      // Scrapes the SRS details straight out of the attached text/PDF/DOCX file (a requirements
      // brief the human already has written up), same as typing them in by hand. Not streamed --
      // there's no meaningful "live" moment while the file is being parsed server-side.
      respondWithDocument.mutate({ file: attachedFile, reply: trimmed });
      return;
    }

    // Live, token-by-token reply (ChatGPT/Claude-style) -- the agent's reaction+questions "type"
    // in as they're generated instead of appearing all at once after a blocking wait.
    setPendingHumanReply(trimmed);
    handleReplyStream({ reply: trimmed })
      .then((result) => {
        // The whole turn (human_reply + the agent's reaction/questions) is only ever persisted
        // atomically by the stream's "done" event -- stopping partway through means NOTHING was
        // saved server-side, unlike ChatGPT/Claude where the human's own message is durable the
        // instant it's sent. Give the typed text back to the composer instead of silently losing
        // it, so stopping never costs the human their own words.
        if (result?.aborted) setReplyText(trimmed);
      })
      .finally(() => setPendingHumanReply(null));
  }

  const isAgentRunning = runningStage === "requirement" || isReplying || editTurnStream.isPending;
  const showComposer = conversation && !isConfirmed && !isGenerating && !showManualForm;
  // Editing a past reply discards it and everything after it, then regenerates -- only safe while
  // the conversation is still in the gathering phase, same as replying normally.
  const canEditTurns = showComposer;

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-4">
      <ChatHeader feature={feature} runningStage={runningStage} />

      <div className="flex-1 min-h-0 overflow-y-auto py-3 flex flex-col gap-3">
        {isLoading ? (
          <LoadingSpinner label="Loading conversation..." />
        ) : !conversation ? (
          <div className="flex flex-col gap-3 max-w-xl">
            <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">Talk to the Requirement Agent</h3>
            <p className="text-xs text-gray-400 dark:text-gray-500 -mt-2">
              Start from your rough description -- the agent will ask what's missing, prioritizing
              what matters most for a correct architecture and design.
            </p>
            <ErrorBanner error={start.error} fallback="Failed to start the conversation." />
            <button
              onClick={() => start.mutate()}
              disabled={start.isPending}
              className="self-start bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white text-sm font-semibold py-2 px-4 rounded-md"
            >
              {start.isPending ? "Starting..." : "Start Conversation"}
            </button>
            {start.isPending && <LoadingSpinner label="Reading the feature description..." />}
          </div>
        ) : showManualForm ? (
          <RequirementRunForm featureId={featureId} feature={feature} />
        ) : (
          <>
            {conversation.turn_history.map((turn) => {
              // Once a turn is being edited, every turn after it is about to be discarded (see
              // handleEditTurn) -- hide them immediately rather than showing them for a moment
              // and then having them vanish once the regeneration actually lands.
              if (editingContext && turn.turn_index > editingContext.turnIndex) return null;

              const isBeingEdited = editingContext?.turnIndex === turn.turn_index;

              return (
                <div key={turn.turn_index} className="flex flex-col gap-3">
                  {isBeingEdited ? (
                    <>
                      <HumanBubble text={editingContext.pendingReply} />
                      <LiveReactionBubble
                        reactionText={extractStreamingJsonStringField(editStreamedText, "reaction")}
                        hasStarted={editStreamStarted}
                      />
                      <button
                        type="button"
                        onClick={stopEditTurnStream}
                        className="self-start text-xs font-semibold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 underline"
                      >
                        Stop
                      </button>
                    </>
                  ) : (
                    <>
                      {turn.human_reply && (
                        <HumanBubble
                          text={turn.human_reply}
                          onEdit={canEditTurns ? (newReply) => handleEditTurn(turn.turn_index, newReply) : null}
                          isEditPending={editTurnStream.isPending}
                        />
                      )}
                      <AgentTurnBubble turn={turn} />
                    </>
                  )}
                </div>
              );
            })}

            {pendingHumanReply && <HumanBubble text={pendingHumanReply} />}
            {respondStream.isPending && (
              <LiveReactionBubble
                reactionText={extractStreamingJsonStringField(replyStreamedText, "reaction")}
                hasStarted={replyStreamStarted}
              />
            )}

            <ErrorBanner error={editTurnStream.error} fallback="Failed to save your edit." />

            {isConfirmed ? (
              <div className="bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded-lg px-3 py-2.5">
                <p className="text-sm text-green-800 dark:text-green-300 font-semibold">
                  Confirmed -- the final SRS has been generated and is awaiting approval in the Result panel.
                </p>
              </div>
            ) : isGenerating ? (
              <div className="flex items-center justify-between gap-2 bg-accent-50 dark:bg-accent-500/10 border border-accent-200 dark:border-accent-500/30 rounded-lg px-3 py-2.5">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="relative flex h-2 w-2 flex-shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-600" />
                  </span>
                  <p className="text-sm text-accent-800 dark:text-accent-300 font-semibold truncate">
                    Generating the final SRS -- watch it stream live in the Result panel &rarr;
                  </p>
                </div>
                {confirmStream.isPending && (
                  <button
                    type="button"
                    onClick={stopConfirmStream}
                    className="text-xs font-semibold text-accent-700 dark:text-accent-300 hover:text-accent-900 dark:hover:text-accent-100 underline flex-shrink-0"
                  >
                    Stop
                  </button>
                )}
              </div>
            ) : (
              <>
                <ErrorBanner error={respondStream.error} fallback="Failed to send your reply." />
                <ErrorBanner error={respondWithDocument.error} fallback="Failed to process the attached document." />
                <ErrorBanner error={confirmStream.error} fallback="Failed to generate the SRS." />
                <QualityGateBanner
                  qualityGate={conversation.quality_gate}
                  onConfirm={handleConfirm}
                  isConfirming={isGenerating}
                  disabled={isReplying}
                />
              </>
            )}
          </>
        )}
      </div>

      {conversation && !isConfirmed && !isGenerating && (
        <div className="flex-shrink-0 flex items-center justify-between pb-2">
          <button
            onClick={() => setShowManualForm((v) => !v)}
            className="text-xs text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300 font-semibold underline"
          >
            {showManualForm ? "Use the conversation instead" : "Prefer a detailed form instead?"}
          </button>
          <button
            onClick={() => reset.mutate()}
            disabled={reset.isPending}
            className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 underline"
          >
            Start over
          </button>
        </div>
      )}

      {showComposer && (
        <form onSubmit={handleReplySubmit} className="flex-shrink-0">
          <ChatComposerBox
            value={replyText}
            onChange={(event) => setReplyText(event.target.value)}
            placeholder="Answer the question(s) above, attach a document, or add anything else..."
            disabled={isReplying || editTurnStream.isPending}
            pending={isReplying}
            onStop={respondStream.isPending ? stopReplyStream : undefined}
            selectedAgent={selectedAgent}
            onSelectAgent={selectAgent}
            isAgentRunning={isAgentRunning}
            allowFileAttach
            attachedFile={attachedFile}
            onAttachFile={setAttachedFile}
            onRemoveAttachedFile={() => setAttachedFile(null)}
          />
        </form>
      )}
    </div>
  );
}
