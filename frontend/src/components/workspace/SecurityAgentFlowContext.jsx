import { createContext, useContext } from "react";
import { useRunSecurityAgent } from "../../hooks/useSecurityAgent";

const SecurityAgentFlowContext = createContext(null);

// Mirrors UiuxAgentFlowContext.jsx's own reasoning, at the smallest scale that reasoning needs:
// SecurityReportView (the stage's own Run/Re-run Scan button) and ResultTab (the Coder-Agent-
// approval popup's auto-triggered first scan) both need to observe the SAME useRunSecurityAgent
// mutation -- two independent instances would each hold their own separate `isPending`, so a scan
// started from the approval popup would show no visible progress anywhere once the chat switches
// to the Security stage. Security Agent has no streaming route (a scan is one plain POST, see
// useSecurityAgent.js's own docstring), so this wraps just that one mutation, not a bigger flow
// hook the way Domain/Architecture/UI-UX Agent's own contexts do.
export function SecurityAgentFlowProvider({ featureId, children }) {
  const runSecurity = useRunSecurityAgent(featureId);
  return <SecurityAgentFlowContext.Provider value={{ runSecurity }}>{children}</SecurityAgentFlowContext.Provider>;
}

export function useSecurityAgentFlowContext() {
  const ctx = useContext(SecurityAgentFlowContext);
  if (!ctx) {
    throw new Error("useSecurityAgentFlowContext must be used within a SecurityAgentFlowProvider");
  }
  return ctx;
}
