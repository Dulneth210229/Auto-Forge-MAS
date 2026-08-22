import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { getQaChatHistory, qaChatStream } from "../api/agents";

// Real, persisted chat history -- reloading the page must not lose the conversation (direct
// user request). Backed by GET /qa/chat (store.qa_conversations).
export function useQaChatHistory(featureId) {
  return useQuery({
    queryKey: ["qaChatHistory", featureId],
    queryFn: () => getQaChatHistory(featureId),
    enabled: Boolean(featureId),
  });
}

// Simpler than useCoderAgentFlow.js's revise-stream half -- QA chat is pure Q&A (see
// qa_agent/prompt.py's QA_CHAT_SYSTEM_PROMPT), so there's no phase/tool_activity events, just
// token + done + error, same as every other streaming flow's token half.
export function useQaChatFlow(featureId) {
  const queryClient = useQueryClient();
  const [streamedText, setStreamedText] = useState("");
  const [streamStarted, setStreamStarted] = useState(false);
  const [streamError, setStreamError] = useState(null);
  // The human's own message, held here (not just the composer's own local state, which clears
  // on submit) so it can render as an optimistic bubble for the whole in-flight duration --
  // without this, real testing showed the typed question vanishes from the screen entirely the
  // instant Send is clicked (the composer clears, but nothing else shows it) and doesn't
  // reappear until the full exchange finishes and history refetches, which on this project's
  // own local models routinely takes well over a minute. Same fix shape as
  // DomainAgentChat.jsx's `pendingHumanReply`.
  const [pendingHumanMessage, setPendingHumanMessage] = useState(null);
  const abortRef = useRef(null);

  const chatStream = useMutation({
    mutationFn: (message) => {
      const controller = new AbortController();
      abortRef.current = controller;
      return qaChatStream(
        featureId,
        { message },
        (event) => {
          if (event.type === "token") {
            setStreamStarted(true);
            setStreamedText((current) => current + event.text);
          } else if (event.type === "error") {
            setStreamError(event.message);
          }
        },
        controller.signal
      );
    },
    // Awaited, not fire-and-forget -- a real, confirmed bug (see this project's own item-49
    // precedent for Domain Agent's identical chat): an un-awaited invalidateQueries here lets
    // mutateAsync() resolve (and the optimistic/streamed bubbles unmount) before the fresh,
    // real persisted history has actually landed in the cache, producing a real empty-frame
    // flash between "the streaming bubble disappeared" and "the real bubble appeared."
    onSuccess: async () => {
      // The real, persisted turn (both the human's message and the full assistant reply) was
      // already appended server-side once the stream's "done" event fired -- refetch so the
      // history list picks it up instead of the app trying to reconstruct it from streamedText.
      await queryClient.invalidateQueries({ queryKey: ["qaChatHistory", featureId] });
    },
  });

  function handleSendMessage(message) {
    setStreamedText("");
    setStreamStarted(false);
    setStreamError(null);
    setPendingHumanMessage(message);
    return chatStream.mutateAsync(message).finally(() => setPendingHumanMessage(null));
  }

  function stopStream() {
    abortRef.current?.abort();
  }

  return {
    chatStream, handleSendMessage, stopStream,
    streamedText, streamStarted, streamError, pendingHumanMessage,
  };
}
