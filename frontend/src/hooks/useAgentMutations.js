import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  reviseArchitecture,
  reviseCoder,
  reviseDomain,
  runArchitecture,
  runCoder,
  runDomain,
  runRequirement,
  runUiux,
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

export function useRunDomain(featureId) {
  return useAgentMutation(featureId, (payload) => runDomain(featureId, payload));
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

export function useRunUiux(featureId) {
  return useAgentMutation(featureId, (payload) => runUiux(featureId, payload));
}

export function useRunCoder(featureId) {
  return useAgentMutation(featureId, (payload) => runCoder(featureId, payload));
}

export function useReviseCoder(featureId) {
  return useAgentMutation(featureId, (payload) => reviseCoder(featureId, payload));
}
