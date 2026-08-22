import { DISPLAY_TIERS, groupFindingsByTier } from "./severityTiers";

// Formats a Security Agent report (the JSON artifact shape saved by security_agent/agent.py's
// run()) into a Coder Agent revision_comment. One line per finding as "[TIER] file:line --
// message", grouped critical-first -- deliberately carries a real `file:line` token per line so
// the Coder Agent's existing _find_well_specified_target_files (_REVISION_FILE_TOKEN_RE,
// coder_agent/agent.py:96) can target the right files with zero Coder-side changes.
export function buildSecurityRevisionComment(report) {
  const groups = groupFindingsByTier(report?.findings || []);

  const lines = ["Fix the following security findings reported by the Security Agent:", ""];

  for (const tier of DISPLAY_TIERS) {
    const findings = groups[tier];
    if (findings.length === 0) continue;

    for (const finding of findings) {
      const loc = finding.line ? `${finding.file}:${finding.line}` : finding.file;
      lines.push(`[${tier.toUpperCase()}] ${loc} -- ${finding.message} (${finding.cwe})`);
    }
  }

  return lines.join("\n");
}
