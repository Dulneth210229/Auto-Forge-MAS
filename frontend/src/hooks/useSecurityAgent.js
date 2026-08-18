import { useMutation, useQueryClient } from "@tanstack/react-query";
import { runSecurity } from "../api/agents";

// Security Agent has no chat/revision flow (see MANUAL_RUN_STAGES/REVISABLE_STAGES in
// pipelineStages.js) -- just a direct re-run trigger, so a plain useMutation is enough here,
// unlike the streaming useXAgentFlow hooks the other agents use.
export function useRunSecurityAgent(featureId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => runSecurity(featureId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artifacts", featureId] });
      queryClient.invalidateQueries({ queryKey: ["feature", featureId] });
      queryClient.invalidateQueries({ queryKey: ["events", featureId] });
      queryClient.invalidateQueries({ queryKey: ["graphStatus", featureId] });
    },
  });
}
