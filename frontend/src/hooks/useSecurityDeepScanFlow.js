import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { runSecurityDeepScanStream } from "../api/agents";

// Live, streamed AI-model deep scan -- mirrors useArchitectureAgentFlow.js's runStream half
// exactly (same NDJSON-over-fetch mechanism, same AbortController-per-call "stop" pattern, same
// awaited-onSuccess fix for the "reply disappears instantly" race -- see that hook's own comment
// for the full story). Tracks `progress` ({current, total, percent}) and `phaseLabel` instead of
// Architecture's streamed token text, since this scan has no token stream of its own -- just real
// per-batch progress events.
export function useSecurityDeepScanFlow(featureId) {
  const queryClient = useQueryClient();

  const [progress, setProgress] = useState(null);
  const [phaseLabel, setPhaseLabel] = useState(null);
  const [scanError, setScanError] = useState(null);

  const abortRef = useRef(null);

  async function invalidateAfterCompletion() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["artifacts", featureId] }),
      queryClient.invalidateQueries({ queryKey: ["feature", featureId] }),
      queryClient.invalidateQueries({ queryKey: ["events", featureId] }),
      queryClient.invalidateQueries({ queryKey: ["graphStatus", featureId] }),
    ]);
  }

  const deepScanStream = useMutation({
    mutationFn: (payload) => {
      const controller = new AbortController();
      abortRef.current = controller;
      return runSecurityDeepScanStream(
        featureId,
        payload,
        (event) => {
          if (event.type === "phase") {
            setPhaseLabel(event.label);
          } else if (event.type === "progress") {
            setPhaseLabel(event.label);
            setProgress({
              current: event.current,
              total: event.total,
              percent: event.total > 0 ? Math.round((event.current / event.total) * 100) : 0,
            });
          } else if (event.type === "error") {
            // The backend route always converts an uncaught exception into a real
            // {"type": "error"} NDJSON line before the stream ends -- but the streamed request's
            // own promise still resolves normally for it (only a genuine network/HTTP failure
            // rejects), so without this branch a real backend crash was completely invisible.
            setScanError(event.message);
          }
        },
        controller.signal
      );
    },
    onSuccess: invalidateAfterCompletion,
  });

  function handleDeepScanStream(payload = {}) {
    setProgress(null);
    setPhaseLabel(null);
    setScanError(null);
    return deepScanStream.mutateAsync(payload);
  }

  function stopDeepScanStream() {
    abortRef.current?.abort();
  }

  return {
    deepScanStream,
    handleDeepScanStream,
    stopDeepScanStream,
    progress,
    phaseLabel,
    scanError,
  };
}
