// Mirrors app/services/graph_orchestrator_service.py's STAGE_SEQUENCE / GATED_STAGES /
// AUTO_APPROVED_STAGES -- single source of truth for the frontend's pipeline UI.
// Keep in sync if the backend's stage list ever changes.

export const STAGE_SEQUENCE = ["requirement", "domain", "architecture", "uiux", "coder", "security", "qa"];

// "uiux" is back here per direct user request: human approval is required again for the UI/UX
// stage's output (only the Preview Screenshot is the human's approval surface on the backend).
export const GATED_STAGES = ["requirement", "domain", "architecture", "uiux", "coder"];

export const AUTO_APPROVED_STAGES = ["security", "qa"];

// Every real, selectable agent stage in pipeline order (excludes security/qa/deployment, which
// have no agent implementation yet -- see PLACEHOLDER_STAGES below). Distinct from GATED_STAGES:
// this is "which stages are real agents a human can chat with / see status for," not "which
// stages pause for a human approval gate" -- uiux belongs here but not in GATED_STAGES.
export const SELECTABLE_AGENT_STAGES = ["requirement", "domain", "architecture", "uiux", "coder"];

// Stages the human triggers directly via a "Run" button/form -- these are pass-through
// no-ops inside the LangGraph itself (see agent.py's own run() methods, called outside the
// graph). Everything else in GATED_STAGES runs automatically once the prior stage is approved.
export const MANUAL_RUN_STAGES = ["requirement", "architecture"];

// Stages with no real backend implementation yet -- shown greyed-out in the tracker.
export const PLACEHOLDER_STAGES = ["security", "qa", "deployment"];

export const STAGE_LABELS = {
  requirement: "Requirement",
  domain: "Domain",
  architecture: "Architecture",
  uiux: "UI/UX",
  coder: "Coder",
  security: "Security",
  qa: "QA",
  deployment: "Deployment",
};

// Cosmetic framing only -- who this stage's output is "for," not a real permission system.
// This app has no authentication/authorization at all; these labels exist purely so a human
// looking at the dashboard understands whose job each stage represents.
export const STAGE_ROLE_LABELS = {
  requirement: "Business Analyst",
  domain: "Domain Expert",
  architecture: "Solution Architect",
  uiux: "UI/UX Designer",
  coder: "Tech Lead",
  security: "Security Engineer",
  qa: "QA Engineer",
  deployment: "DevOps Engineer",
};

// Stages with a real POST .../revise endpoint.
export const REVISABLE_STAGES = ["requirement", "domain", "architecture", "uiux", "coder"];

// Generous, real-world-observed timeouts (ms) before a "processing" auto-run stage is shown
// as "possibly stuck" rather than an indefinite spinner. The graph itself gives no distinct
// failure signal (a crashed node just leaves graph-status.next parked forever), so this is a
// UX safety net, not a definitive error state -- polling continues regardless.
export const STUCK_TIMEOUT_MS = {
  domain: 90_000,
  uiux: 5 * 60_000,
  coder: 15 * 60_000,
};
