import { useArtifactContent } from "../../hooks/useArtifacts";
import { useSecurityAgentFlowContext } from "../workspace/SecurityAgentFlowContext";
import { DISPLAY_TIERS, groupFindingsByTier, toDisplayTier } from "../../lib/severityTiers";
import SeverityBadge from "./SeverityBadge";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorBanner from "../common/ErrorBanner";

const GATE_BANNER_STYLE = {
  fail: "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30 text-red-800 dark:text-red-300",
  review: "bg-orange-50 dark:bg-orange-500/10 border-orange-200 dark:border-orange-500/30 text-orange-800 dark:text-orange-300",
  pass: "bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/30 text-green-800 dark:text-green-300",
};

const GATE_BANNER_TEXT = {
  fail: "Critical vulnerabilities found -- review before proceeding.",
  review: "Moderate-severity findings to review.",
  pass: "No Critical or Moderate findings.",
};

const TIER_HEADING = { critical: "Critical", moderate: "Moderate", warning: "Warning" };

function FindingRow({ finding }) {
  const loc = finding.line ? `${finding.file}:${finding.line}` : finding.file;
  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <SeverityBadge tier={toDisplayTier(finding.severity)} />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-gray-800 dark:text-gray-200">{finding.message}</p>
        <p className="text-xs text-gray-400 dark:text-gray-500 font-mono mt-0.5">
          {finding.rule_id} -- {loc} -- {finding.cwe}
        </p>
        {finding.root_cause && (
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
            <span className="font-semibold">Root cause:</span> {finding.root_cause}
          </p>
        )}
        {finding.recommendation && (
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
            <span className="font-semibold">Suggested fix:</span> {finding.recommendation}
          </p>
        )}
      </div>
    </div>
  );
}

const SCAN_TYPE_LABEL = {
  ai_model_deep_scan: "AI model deep scan",
  standard: "Standard scan",
};

// Renders a Security Agent report (the JSON artifact security_agent/agent.py's run() saves),
// grouped into Critical/Moderate/Warning per the severity taxonomy (severityTiers.js, mirroring
// the backend's severity.py). Rendered from ResultTab.jsx's `stage === "security"` branch instead
// of the generic ArtifactContentView, since a flat JSON tree doesn't serve this report's own
// "categorize and color-code" requirement the way a dedicated view does.
//
// Deliberately has NO "send to Coder Agent" action of its own -- the report now requires real
// human approval (agent.py's run() saves it PENDING, not auto-approved), and choosing to send it
// to the Coder Agent only happens through SecurityDecisionDialog.jsx, which opens right after
// approving. Letting this view trigger that same action directly would let a human bypass
// approval entirely, defeating the point of requiring it. "Re-run Scan" stays here since it's an
// independent, non-approval-gated action (just re-scanning, not accepting/escalating anything).
export default function SecurityReportView({ artifact }) {
  const { data, isLoading, error } = useArtifactContent(artifact?.artifact_id ?? null);
  const report = data?.content_json;
  // Shared with ResultTab.jsx's Coder-Agent-approval auto-trigger (see SecurityAgentFlowContext's
  // own docstring) -- not a fresh useRunSecurityAgent(featureId) instance, so a scan started from
  // the approval popup shows its real progress here too, not just wherever it was started.
  const { runSecurity, runSecurityDeepScan } = useSecurityAgentFlowContext();
  const anyScanPending = runSecurity.isPending || runSecurityDeepScan.isPending;

  // No report exists yet (never scanned, or the feature has no generated code yet) -- Security
  // Agent has no revise() flow (a re-run IS the whole operation), so this empty-state action is
  // one of two real ways to trigger a first run (SecurityAgentChat's own empty-state button is
  // the other, sharing the same useSecurityAgentFlowContext() mutation -- see ResultTab.jsx's own
  // comment on why this branch renders regardless of whether an artifact exists).
  if (!artifact) {
    return (
      <div className="flex flex-col items-start gap-3">
        <p className="text-sm text-gray-400 dark:text-gray-500 italic">
          No security scan has been run yet for this feature.
        </p>
        <ErrorBanner error={runSecurity.error} fallback="Failed to run the security scan." />
        <ErrorBanner error={runSecurityDeepScan.error} fallback="Failed to run the AI model scan." />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => runSecurity.mutate({})}
            disabled={anyScanPending}
            className="text-sm bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white font-semibold px-3 py-1.5 rounded-md"
          >
            {runSecurity.isPending ? "Scanning..." : "Run Security Scan"}
          </button>
          <button
            type="button"
            onClick={() => runSecurityDeepScan.mutate({})}
            disabled={anyScanPending}
            title="Have the configured AI model read the real generated source code directly and look for vulnerabilities"
            className="text-sm bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold px-3 py-1.5 rounded-md"
          >
            {runSecurityDeepScan.isPending ? "Scanning with model..." : "Scan with AI Model"}
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return <LoadingSpinner label="Loading security report..." />;
  }

  if (error || !report) {
    return <ErrorBanner error={error} fallback="Failed to load the security report." />;
  }

  const groups = groupFindingsByTier(report.findings || []);
  const hasFindings = (report.findings || []).length > 0;

  return (
    <div className="flex flex-col gap-5">
      <div className={`rounded-lg border px-4 py-3 flex items-center justify-between gap-3 ${GATE_BANNER_STYLE[report.gate_decision] || ""}`}>
        <div>
          <p className="text-sm font-bold">{GATE_BANNER_TEXT[report.gate_decision] || "Scan complete."}</p>
          <p className="text-xs opacity-80 mt-0.5">
            {report.findings_count} finding(s) -- {report.critical_count} critical, {report.moderate_count} moderate,{" "}
            {report.warning_count} warning
          </p>
          <p className="text-xs opacity-70 mt-0.5">
            Scan type: {SCAN_TYPE_LABEL[report.scan_type] || "Standard scan"}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            type="button"
            onClick={() => runSecurity.mutate({})}
            disabled={anyScanPending}
            title="Re-scan the current code without going through the Coder Agent"
            className="text-sm bg-white dark:bg-white/10 hover:bg-gray-50 dark:hover:bg-white/20 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 disabled:opacity-50 font-semibold px-3 py-1.5 rounded-md"
          >
            {runSecurity.isPending ? "Scanning..." : "Re-run Scan"}
          </button>
          <button
            type="button"
            onClick={() => runSecurityDeepScan.mutate({})}
            disabled={anyScanPending}
            title="Have the configured AI model read the real generated source code directly and look for vulnerabilities"
            className="text-sm bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold px-3 py-1.5 rounded-md"
          >
            {runSecurityDeepScan.isPending ? "Scanning with model..." : "Scan with AI Model"}
          </button>
        </div>
      </div>

      <ErrorBanner error={runSecurity.error} fallback="Failed to run the security scan." />
      <ErrorBanner error={runSecurityDeepScan.error} fallback="Failed to run the AI model scan." />

      {!hasFindings ? (
        <p className="text-sm text-gray-400 dark:text-gray-500 italic">No findings from any scan layer.</p>
      ) : (
        DISPLAY_TIERS.map((tier) =>
          groups[tier].length === 0 ? null : (
            <div key={tier}>
              <h4 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">
                {TIER_HEADING[tier]} ({groups[tier].length})
              </h4>
              <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg px-3">
                {groups[tier].map((finding) => (
                  <FindingRow key={finding.id} finding={finding} />
                ))}
              </div>
            </div>
          )
        )
      )}

      <div className="pt-4 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-400 space-y-1">
        <p>
          <span className="font-semibold">Dependency scan:</span> npm audit exit code{" "}
          {report.dependency_scan?.audit_exit_code} (
          {report.dependency_scan?.audit_ran_offline ? "offline" : "online"})
        </p>
        <p>
          <span className="font-semibold">LLM review layer:</span> {report.llm_review_status}
        </p>
      </div>
    </div>
  );
}
