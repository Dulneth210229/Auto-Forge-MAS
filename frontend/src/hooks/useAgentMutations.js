import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  reviseArchitecture,
  reviseCoder,
  reviseDomain,
  reviseRequirement,
  runArchitecture,
  runRequirement,
} from "../api/agents";

function useAgentMutation(featureId, mutationFn) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["graphStatus", featureId] });
      queryClient.invalidateQueries({ queryKey: ["artifacts", featureId] });
      queryClient.invalidateQueries({ queryKey: ["feature", featureId] });
      queryClient.invalidateQueries({ queryKey: ["events", featureId] });
    },
  });
}

export function useRunRequirement(featureId) {
  return useAgentMutation(featureId, (payload) => runRequirement(featureId, payload));
}

export function useReviseRequirement(featureId) {
  return useAgentMutation(featureId, (payload) => reviseRequirement(featureId, payload));
}

export function useReviseDomain(featureId) {
  return useAgentMutation(featureId, (payload) => reviseDomain(featureId, payload));
}

export function useRunArchitecture(featureId) {
  return useAgentMutation(featureId, (payload) => runArchitecture(featureId, payload));
}

export function useReviseArchitecture(featureId) {
  return useAgentMutation(featureId, (payload) => reviseArchitecture(featureId, payload));
}

export function useReviseCoder(featureId) {
  return useAgentMutation(featureId, (payload) => reviseCoder(featureId, payload));
}
