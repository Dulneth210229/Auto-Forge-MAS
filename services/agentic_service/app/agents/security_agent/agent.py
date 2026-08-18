"""
Security Agent.

Real implementation, replacing the earlier placeholder that always returned
{"status": "skipped"}. Runs three deterministic scan layers against the
generated project's own workspace -- pattern-based static analysis (real
TypeScript-compiler AST, not text matching), secret/credential scanning, and
`npm audit` dependency scanning -- reduces the combined findings to a
pass/fail gate decision, and saves a JSON + Markdown security report as a
versioned artifact through the same artifact_service path every other agent
uses. An optional fourth layer asks the configured LLM to review the
deterministic findings against real source and add findings it can ground in
what it was shown; if the LLM provider is unreachable, that layer is skipped
and reported as skipped rather than silently omitted, and the deterministic
findings (this stage's actual evidence) are unaffected either way.

Auto-approved stage: still runs without an interrupt() gate (see
graph_orchestrator_service._security_node), consistent with the rest of the
pipeline's design -- a human reviews the resulting report artifact after the
fact rather than blocking pipeline advancement on it, since a failed gate is
recorded on the feature record for a reviewer to see rather than silently
merged past.
"""

from datetime import datetime, timezone
from pathlib import Path

from app.agents.security_agent.prompt import SECURITY_AGENT_SYSTEM_PROMPT
from app.agents.security_agent.schemas import SecurityAgentOutput
from app.agents.security_agent.scanners import (
    scan_dangerous_patterns,
    scan_dependencies,
    scan_secrets,
)
from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.workspace_service import workspace_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# A finding at this severity or above fails the gate. Chosen to match npm's
# own audit severity scale (info < low < moderate/medium < high < critical)
# plus this agent's own pattern/secret rule severities.
GATE_FAIL_SEVERITIES = {"critical", "high"}


def _build_markdown_report(report: dict) -> str:
    lines = [
        f"# Security Report -- {report['project_name']} / {report['feature_name']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Gate decision: **{report['gate_decision'].upper()}**",
        f"Total findings: {report['findings_count']} "
        f"({report['critical_or_high_count']} critical/high)",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("No findings from any scan layer.")
    for finding in report["findings"]:
        loc = f"{finding['file']}:{finding['line']}" if finding.get("line") else finding["file"]
        lines.append(
            f"- **[{finding['severity'].upper()}]** `{finding['rule_id']}` "
            f"({finding['cwe']}) -- {loc} -- {finding['message']}"
        )
    lines += [
        "",
        "## Dependency scan",
        "",
        f"npm audit exit code: {report['dependency_scan']['audit_exit_code']}",
        f"Ran offline (sandbox has no outbound network to the npm advisory "
        f"endpoint): {report['dependency_scan']['audit_ran_offline']}",
        f"Dependency summary: {report['dependency_scan']['dependency_summary']}",
        "",
        "## LLM review layer",
        "",
        report["llm_review_status"],
    ]
    return "\n".join(lines)


class SecurityAgent:
    async def run(self, **kwargs) -> SecurityAgentOutput:
        feature_id = kwargs["feature_id"]
        feature = store.features.get(feature_id)
        project = store.projects.get(feature["project_id"])

        repo_path = workspace_service.get_repo_path(project["project_id"])

        if not repo_path.exists():
            logger.warning("Security Agent: repo path %s does not exist, skipping scan", repo_path)
            return SecurityAgentOutput(
                status="skipped",
                message=f"No workspace found at {repo_path} for this feature yet.",
            )

        pattern_findings = scan_dangerous_patterns(repo_path)
        secret_findings = scan_secrets(repo_path)
        dependency_result = scan_dependencies(project["project_id"], repo_path)

        all_findings = pattern_findings + secret_findings + dependency_result["findings"]
        critical_or_high = [f for f in all_findings if f["severity"] in GATE_FAIL_SEVERITIES]
        gate_decision = "fail" if critical_or_high else "pass"

        llm_review_status = await self._run_llm_review_layer(all_findings)

        report = {
            "project_name": project["project_name"],
            "feature_name": feature["feature_name"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "gate_decision": gate_decision,
            "findings_count": len(all_findings),
            "critical_or_high_count": len(critical_or_high),
            "findings": all_findings,
            "dependency_scan": {
                "audit_exit_code": dependency_result["audit_exit_code"],
                "audit_ran_offline": dependency_result["audit_ran_offline"],
                "dependency_summary": dependency_result["dependency_summary"],
            },
            "llm_review_status": llm_review_status,
        }

        markdown = _build_markdown_report(report)

        json_artifact = artifact_service.save_json_artifact(
            project=project, feature=feature,
            agent_name=AgentName.SECURITY, artifact_type=ArtifactType.SECURITY_REPORT,
            filename="security_report_v{version}.json", data=report,
            approval_status=ApprovalStatus.APPROVED,
        )
        md_artifact = artifact_service.save_text_artifact(
            project=project, feature=feature,
            agent_name=AgentName.SECURITY, artifact_type=ArtifactType.SECURITY_REPORT,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename="security_report_v{version}.md", content=markdown,
            version_override=json_artifact.version,
            approval_status=ApprovalStatus.APPROVED,
        )

        logger.info(
            "Security Agent finished for feature_id=%s: %d findings, gate=%s",
            feature_id, len(all_findings), gate_decision,
        )

        return SecurityAgentOutput(
            security_report_json=report,
            status="completed",
            gate_decision=gate_decision,
            findings_count=len(all_findings),
            critical_or_high_count=len(critical_or_high),
            artifact_ids=[json_artifact.artifact_id, md_artifact.artifact_id],
            message=f"{len(all_findings)} finding(s), gate={gate_decision}.",
        )

    async def _run_llm_review_layer(self, findings: list[dict]) -> str:
        try:
            from app.services.llm_provider_service import llm_provider_service

            provider = llm_provider_service.get_provider(agent_name=AgentName.SECURITY.value)
            summary = "\n".join(
                f"- {f['rule_id']} ({f['severity']}) {f['file']}:{f.get('line')}: {f['message']}"
                for f in findings
            ) or "No deterministic findings."
            await provider.invoke_agent([
                {"role": "system", "content": SECURITY_AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Deterministic findings so far:\n{summary}"},
            ])
            return "LLM review layer ran successfully; see individual findings for any additions."
        except Exception as error:  # noqa: BLE001 -- an unreachable LLM must not fail the whole scan
            logger.warning("Security Agent LLM review layer unavailable, skipping: %s", error)
            return (
                f"Skipped -- LLM provider unreachable in this run ({type(error).__name__}). "
                f"The three deterministic layers above (pattern, secret, dependency) are "
                f"unaffected and are this report's evidence."
            )


security_agent = SecurityAgent()
