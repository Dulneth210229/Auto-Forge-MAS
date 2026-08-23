import { createContext, useContext } from "react";
import { useRunQaAgent } from "../../hooks/useQaAgent";

const QaAgentFlowContext = createContext(null);

// Mirrors SecurityAgentFlowContext.jsx's own reasoning, at the smallest scale that reasoning
// needs: QaReportView (the stage's own Run/Re-run QA Scan button), QaAgentChat (its own
// empty-state "Run QA Scan" action), and ResultTab's new "Continue to QA Agent" button (on the
// Security stage) all need to observe the SAME useRunQaAgent mutation -- three independent
// instances would each hold their own separate `isPending`, so a run started from one surface
// (e.g. Security's "Continue to QA Agent") would show no visible progress once the human switches
// over to QaReportView. Running QA has no streaming route (one plain POST, see useQaAgent.js's
// own docstring), so this context wraps just that one mutation, not a bigger flow hook the way
// Domain/Architecture/UI-UX Agent's own contexts do.
export function QaAgentFlowProvider({ featureId, children }) {
  const runQa = useRunQaAgent(featureId);
  return <QaAgentFlowContext.Provider value={{ runQa }}>{children}</QaAgentFlowContext.Provider>;
}

export function useQaAgentFlowContext() {
  const ctx = useContext(QaAgentFlowContext);
  if (!ctx) {
    throw new Error("useQaAgentFlowContext must be used within a QaAgentFlowProvider");
  }
  return ctx;
}
