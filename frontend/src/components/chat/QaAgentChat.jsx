import { useState } from "react";
import { useQaChatFlow, useQaChatHistory } from "../../hooks/useQaChatFlow";
import { useRunQaAgent } from "../../hooks/useQaAgent";
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

function QaChatBubble({ turn }) {
  const isUser = turn.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-accent-600 dark:bg-accent-500 text-white rounded-tr-sm"
            : "bg-gray-100 dark:bg-white/10 text-gray-800 dark:text-gray-200 rounded-tl-sm"
        }`}
      >
        {!isUser && <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">QA Agent</p>}
        {turn.content || <span className="italic opacity-60">...</span>}
      </div>
    </div>
  );
}

// QA Agent's own dedicated chat -- deliberately NOT built on ChatBubble/timeline (every other
// agent's chat reconstructs its conversation from artifact/event history, since those agents'
// "chat" IS their run/revise activity log). QA chat is genuinely different: pure Q&A about an
// already-generated report, backed by its own real, persisted turn history
// (store.qa_conversations, see useQaChatFlow.js's useQaChatHistory) rather than being derived
// from artifacts. Unlike Security Agent (deliberately no chat at all), QA gets a real one here,
// per direct user request for live, streaming, history-preserving discussion of test results.
export default function QaAgentChat({ featureId, feature, runningStage, selectedAgent, selectAgent, allArtifacts }) {
  const { data: history, isLoading: isLoadingHistory } = useQaChatHistory(featureId);
  const {
    chatStream, handleSendMessage, stopStream,
    streamedText, streamStarted, streamError, pendingHumanMessage,
  } = useQaChatFlow(featureId);
  const runQa = useRunQaAgent(featureId);
  const [message, setMessage] = useState("");

  const hasReport = (allArtifacts || []).some((a) => a.artifact_type === "qa_report");
  const turns = history?.turns || [];
  const isAgentRunning = runningStage === "qa" || chatStream.isPending || runQa.isPending;

  function handleSubmit(event) {
    event.preventDefault();
    if (chatStream.isPending) return;
    const trimmed = message.trim();
    if (!trimmed) return;
    setMessage("");
    handleSendMessage(trimmed);
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 p-4">
      <ChatHeader feature={feature} runningStage={runningStage} />

      <div className="flex-1 min-h-0 overflow-y-auto py-3 flex flex-col gap-3">
        {!hasReport && (
          <div className="bg-accent-50 dark:bg-accent-500/10 border border-accent-200 dark:border-accent-500/30 rounded-md px-3 py-2.5">
            <p className="text-sm font-semibold text-accent-900 dark:text-accent-200">
              No QA scan has been run yet for this feature.
            </p>
            <ErrorBanner error={runQa.error} fallback="Failed to run the QA scan." />
            <button
              type="button"
              onClick={() => runQa.mutate({})}
              disabled={runQa.isPending}
              className="mt-2 text-xs font-semibold bg-white dark:bg-white/10 hover:bg-accent-100 dark:hover:bg-white/20 disabled:opacity-50 text-accent-700 dark:text-accent-300 border border-accent-300 dark:border-accent-500/40 rounded-full px-3 py-1"
            >
              {runQa.isPending ? "Running..." : "Run QA Scan"}
            </button>
          </div>
        )}

        {isLoadingHistory ? (
          <LoadingSpinner label="Loading chat history..." />
        ) : turns.length === 0 && !chatStream.isPending ? (
          <p className="text-sm text-gray-400 dark:text-gray-500 italic">
            No messages yet. Ask about the QA report below -- e.g. "why did the item unit test fail?"
          </p>
        ) : (
          turns.map((turn, i) => <QaChatBubble key={i} turn={turn} />)
        )}

        {chatStream.isPending && pendingHumanMessage && (
          <QaChatBubble turn={{ role: "user", content: pendingHumanMessage }} />
        )}
        {chatStream.isPending && streamStarted && <QaChatBubble turn={{ role: "assistant", content: streamedText }} />}

        <ErrorBanner error={chatStream.error || (streamError && { message: streamError })} fallback="QA chat request failed." />
      </div>

      <div className="flex-shrink-0 pt-1">
        <form onSubmit={handleSubmit}>
          <ChatComposerBox
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            disabled={false}
            pending={chatStream.isPending}
            onStop={stopStream}
            selectedAgent={selectedAgent}
            onSelectAgent={selectAgent}
            isAgentRunning={isAgentRunning}
            placeholder="Ask QA Agent about the test results..."
          />
        </form>
      </div>
    </div>
  );
}
