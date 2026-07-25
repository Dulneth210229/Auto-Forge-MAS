import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getLlmSettings, testLlmSettings, updateLlmSettings } from "../api/llmSettings";
import {
  clearAgentLlmSettings,
  listAgentLlmSettings,
  testAgentLlmSettings,
  updateAgentLlmSettings,
} from "../api/agentLlmSettings";

export function useLlmSettings() {
  return useQuery({ queryKey: ["llmSettings"], queryFn: getLlmSettings });
}

export function useUpdateLlmSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateLlmSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llmSettings"] });
    },
  });
}

export function useTestLlmSettings() {
  return useMutation({ mutationFn: testLlmSettings });
}

export function useAgentLlmSettings() {
  return useQuery({ queryKey: ["agentLlmSettings"], queryFn: listAgentLlmSettings });
}

export function useUpdateAgentLlmSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ agentName, update }) => updateAgentLlmSettings(agentName, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentLlmSettings"] });
    },
  });
}

export function useClearAgentLlmSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentName) => clearAgentLlmSettings(agentName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentLlmSettings"] });
    },
  });
}

export function useTestAgentLlmSettings() {
  return useMutation({
    mutationFn: ({ agentName, prompt }) => testAgentLlmSettings(agentName, { prompt }),
  });
}
