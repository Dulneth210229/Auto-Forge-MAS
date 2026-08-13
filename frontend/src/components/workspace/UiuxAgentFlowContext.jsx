import { createContext, useContext } from "react";
import { useRunUiux } from "../../hooks/useAgentMutations";

const UiuxAgentFlowContext = createContext(null);

// Mirrors DomainAgentFlowContext.jsx's shape, but lighter -- UI/UX Agent has no streaming backend
// route (unlike Domain/Architecture), so there's no stream state to manage, just one shared
// useRunUiux mutation instance. ResultTab (to auto-trigger a run right after Architecture Plan
// approval) and ChatPanel (the composer's pending/Stop-button state) both need to observe the
// SAME in-flight mutation -- two independent useRunUiux(featureId) calls would each hold their
// own separate pending state, so a run started from ResultTab would never show as running in the
// chat composer.
export function UiuxAgentFlowProvider({ featureId, children }) {
  const runUiux = useRunUiux(featureId);
  return <UiuxAgentFlowContext.Provider value={{ runUiux }}>{children}</UiuxAgentFlowContext.Provider>;
}

export function useUiuxAgentFlowContext() {
  const ctx = useContext(UiuxAgentFlowContext);
  if (!ctx) {
    throw new Error("useUiuxAgentFlowContext must be used within a UiuxAgentFlowProvider");
  }
  return ctx;
}
