// Formats a QA Agent report (the JSON artifact shape saved by qa_agent/agent.py's run()) into a
// Coder Agent revision_comment -- mirrors securityReportToRevisionComment.js exactly. One line
// per FAILING test case, carrying a real `target_file` token so the Coder Agent's existing
// _find_well_specified_target_files (_REVISION_FILE_TOKEN_RE, coder_agent/agent.py:96) can
// target the right files with zero Coder-side changes.
export function buildQaRevisionComment(report) {
  const failing = (report?.test_cases || []).filter((tc) => tc.status === "failed");

  const lines = ["Fix the following failing tests reported by the QA Agent:", ""];

  for (const tc of failing) {
    const loc = tc.target_function ? `${tc.target_file}::${tc.target_function}` : tc.target_file;
    const failure = tc.failure_message ? tc.failure_message.split("\n")[0] : "no failure detail captured";
    lines.push(`[${tc.category}] ${loc} -- "${tc.name}" -- ${failure}`);
  }

  return lines.join("\n");
}
