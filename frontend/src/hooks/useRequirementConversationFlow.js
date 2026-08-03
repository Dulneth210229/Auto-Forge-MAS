import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  useReplyToRequirementConversationWithDocument,
  useRequirementConversation,
  useResetRequirementConversation,
  useStartRequirementConversation,
} from "./useRequirementConversation";
import {
  confirmRequirementConversationStream,
  editRequirementConversationTurnStream,
  replyToRequirementConversationStream,
  reviseRequirementStream,
} from "../api/agents";

// Everything ChatPanel needs to drive the Requirement Agent's conversational gap-filling flow
// through its own normal composer, instead of a separate bespoke UI -- state/mutations only, no
// JSX, so the chat window's actual markup lives in exactly one place (ChatPanel + ChatComposerBox
// + RequirementConversationParts).
export function useRequirementConversationFlow(featureId) {
  const [streamedText, setStreamedText] = useState("");
  const [streamStarted, setStreamStarted] = useState(false);
  const [replyStreamedText, setReplyStreamedText] = useState("");
  const [replyStreamStarted, setReplyStreamStarted] = useState(false);
  const [revisionStreamedText, setRevisionStreamedText] = useState("");
  const [revisionStreamStarted, setRevisionStreamStarted] = useState(false);
  const [editStreamedText, setEditStreamedText] = useState("");
  const [editStreamStarted, setEditStreamStarted] = useState(false);
  const queryClient = useQueryClient();

  const { data: conversation, isLoading } = useRequirementConversation(featureId);
  const start = useStartRequirementConversation(featureId);
  const respondWithDocument = useReplyToRequirementConversationWithDocument(featureId);
  const reset = useResetRequirementConversation(featureId);

  // Live, token-by-token variant of editTurn (ChatGPT/Claude-style "edit message") -- an edited
  // reply never touches the graph/artifacts/feature (only the conversation document itself
  // changes), so its "done" event's full state is written straight into the query cache instead
  // of triggering a refetch, same as respondStream below.
  const editTurnStream = useMutation({
    mutationFn: ({ turnIndex, reply }) =>
      editRequirementConversationTurnStream(featureId, turnIndex, { reply }, (event) => {
        if (event.type === "token") {
          setEditStreamStarted(true);
          setEditStreamedText((current) => current + event.text);
        } else if (event.type === "done") {
          queryClient.setQueryData(["requirementConversation", featureId], event.state);
        }
      }),
  });

  function handleEditTurnStream(payload) {
    setEditStreamedText("");
    setEditStreamStarted(false);
    return editTurnStream.mutateAsync(payload);
  }

  // Live, token-by-token variant of a normal typed reply (ChatGPT/Claude-style) -- the primary
  // way a human answers the agent's questions. Unlike confirmStream below, a reply never touches
  // the graph/artifacts/feature (only the conversation document itself changes), so its "done"
  // event's full state is written straight into the query cache instead of triggering a refetch
  // -- the UI updates the instant the stream finishes, no extra round trip.
  const respondStream = useMutation({
    mutationFn: (payload) =>
      replyToRequirementConversationStream(featureId, payload, (event) => {
        if (event.type === "token") {
          setReplyStreamStarted(true);
          setReplyStreamedText((current) => current + event.text);
        } else if (event.type === "done") {
          queryClient.setQueryData(["requirementConversation", featureId], event.state);
        }
      }),
  });

  function handleReplyStream(payload) {
    setReplyStreamedText("");
    setReplyStreamStarted(false);
    return respondStream.mutateAsync(payload);
  }

  const confirmStream = useMutation({
    mutationFn: (payload) =>
      confirmRequirementConversationStream(featureId, payload, (event) => {
        if (event.type === "token") {
          setStreamStarted(true);
          setStreamedText((current) => current + event.text);
        }
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["requirementConversation", featureId] });
      queryClient.invalidateQueries({ queryKey: ["graphStatus", featureId] });
      queryClient.invalidateQueries({ queryKey: ["artifacts", featureId] });
      queryClient.invalidateQueries({ queryKey: ["feature", featureId] });
      queryClient.invalidateQueries({ queryKey: ["events", featureId] });
    },
  });

  function handleConfirm(payload) {
    setStreamedText("");
    setStreamStarted(false);
    confirmStream.mutate(payload);
  }

  const isGenerating = confirmStream.isPending || (confirmStream.isSuccess && conversation?.status !== "confirmed");
  const isConfirmed = conversation?.status === "confirmed";

  // Live, token-by-token revision of an ALREADY-confirmed SRS (ChatGPT/Claude-style) -- distinct
  // from respondStream (the pre-confirm gap-filling conversation) and confirmStream (the initial
  // generation): this is what "ask the Requirement Agent to change something" does once a real
  // SRS artifact already exists. A revision touches real artifacts/graph status, so its onSuccess
  // invalidates the same broader query set confirmStream does, not just this hook's own state.
  const reviseStream = useMutation({
    mutationFn: (payload) =>
      reviseRequirementStream(featureId, payload, (event) => {
        if (event.type === "token") {
          setRevisionStreamStarted(true);
          setRevisionStreamedText((current) => current + event.text);
        }
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["graphStatus", featureId] });
      queryClient.invalidateQueries({ queryKey: ["artifacts", featureId] });
      queryClient.invalidateQueries({ queryKey: ["feature", featureId] });
      queryClient.invalidateQueries({ queryKey: ["events", featureId] });
    },
  });

  function handleReviseStream(payload) {
    setRevisionStreamedText("");
    setRevisionStreamStarted(false);
    return reviseStream.mutateAsync(payload);
  }

  return {
    conversation,
    isLoading,
    start,
    respondStream,
    handleReplyStream,
    replyStreamedText,
    replyStreamStarted,
    respondWithDocument,
    editTurnStream,
    handleEditTurnStream,
    editStreamedText,
    editStreamStarted,
    reset,
    confirmStream,
    handleConfirm,
    streamedText,
    streamStarted,
    isGenerating,
    isConfirmed,
    reviseStream,
    handleReviseStream,
    revisionStreamedText,
    revisionStreamStarted,
  };
}
