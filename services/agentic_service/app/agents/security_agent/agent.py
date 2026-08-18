"""
Security Agent.

Runs three deterministic scan layers against the generated project's own workspace --
pattern-based static analysis (real TypeScript-compiler AST, not text matching),
secret/credential scanning, and `npm audit` dependency scanning -- reduces the combined findings
(plus whatever the optional LLM review layer adds, see below) to a Critical/Moderate/Warning
gate decision (severity.py), and saves a JSON + Markdown security report as a versioned artifact
through the same artifact_service path every other agent uses. The report groups findings under
those same three headings for a human (and, via the "send this report to the Coder Agent"
frontend action, for the Coder Agent) to act on.

The optional fourth layer asks the configured LLM to review the deterministic findings summary
and propose additional, clearly-grounded findings; its JSON response is parsed against
SecurityLLMReviewResult and merged into the combined findings BEFORE the gate/counts are
computed. If the LLM provider is unreachable or returns something unparseable, that layer
degrades to an empty findings list and a status note explaining why -- it never fails the whole
scan, and the deterministic findings (this stage's actual evidence) are unaffected either way.

Auto-approved, soft-gate stage: runs without an interrupt() gate (see
graph_orchestrator_service._security_node) -- a Critical gate decision is clearly surfaced on the
report and in the frontend, but never blocks pipeline advancement. A human decides whether to
send the report to the Coder Agent (which automatically re-triggers this agent once that revision
completes) or proceed anyway.
"""

from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from app.agents.security_agent import severity
from app.agents.security_agent.prompt import SECURITY_AGENT_SYSTEM_PROMPT
from app.agents.security_agent.schemas import SecurityAgentOutput, SecurityLLMReviewResult
from app.agents.security_agent.scanners import (
    scan_dangerous_patterns,
    scan_dependencies,
    scan_secrets,
)
from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.workspace_service import workspace_service
from app.utils.json_utils import extract_json_object
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _build_markdown_report(report: dict) -> str:
    lines = [
        f"# Security Report -- {report['project_name']} / {report['feature_name']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Gate decision: **{report['gate_decision'].upper()}**",
        f"Total findings: {report['findings_count']} "
        f"({report['critical_count']} critical, {report['moderate_count']} moderate, "
        f"{report['warning_count']} warning)",
        "",
    ]
    if not report["findings"]:
        lines += ["## Findings", "", "No findings from any scan layer."]
    else:
        findings_by_tier: dict[str, list[dict]] = {tier: [] for tier in severity.DISPLAY_TIERS}
        for finding in report["findings"]:
            findings_by_tier[severity.to_display_tier(finding.get("severity", "unknown"))].append(finding)

        for tier in severity.DISPLAY_TIERS:
            tier_findings = findings_by_tier[tier]
            if not tier_findings:
                continue
            lines += [f"## {tier.capitalize()}", ""]
            for finding in tier_findings:
                loc = f"{finding['file']}:{finding['line']}" if finding.get("line") else finding["file"]
                lines.append(
                    f"- **[{finding['severity'].upper()}]** `{finding['rule_id']}` "
                    f"({finding['cwe']}) -- {loc} -- {finding['message']}"
                )
            lines.append("")

    lines += [
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

        deterministic_findings = pattern_findings + secret_findings + dependency_result["findings"]
        llm_review_status, llm_findings = await self._run_llm_review_layer(deterministic_findings)
        all_findings = deterministic_findings + llm_findings

        tier_counts = severity.count_by_tier(all_findings)
        gate = severity.gate_decision(all_findings)

        report = {
            "project_name": project["project_name"],
            "feature_name": feature["feature_name"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "gate_decision": gate,
            "findings_count": len(all_findings),
            "critical_count": tier_counts["critical"],
            "moderate_count": tier_counts["moderate"],
            "warning_count": tier_counts["warning"],
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
            feature_id, len(all_findings), gate,
        )

        return SecurityAgentOutput(
            security_report_json=report,
            status="completed",
            gate_decision=gate,
            findings_count=len(all_findings),
            critical_count=tier_counts["critical"],
            moderate_count=tier_counts["moderate"],
            warning_count=tier_counts["warning"],
            artifact_ids=[json_artifact.artifact_id, md_artifact.artifact_id],
            message=f"{len(all_findings)} finding(s), gate={gate}.",
        )

    async def _run_llm_review_layer(self, findings: list[dict]) -> tuple[str, list[dict]]:
        """Returns (status message, list of new SecurityFinding-shaped dicts). Never raises --
        an unreachable provider or a malformed/unparseable response both degrade to an empty
        findings list with an explanatory status, so the deterministic findings (this stage's
        actual evidence) are always unaffected."""
        try:
            from app.services.llm_provider_service import llm_provider_service

            provider = llm_provider_service.get_provider(agent_name=AgentName.SECURITY.value)
            summary = "\n".join(
                f"- {f['rule_id']} ({f['severity']}) {f['file']}:{f.get('line')}: {f['message']}"
                for f in findings
            ) or "No deterministic findings."
            raw_output = await provider.invoke_agent([
                {"role": "system", "content": SECURITY_AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Deterministic findings so far:\n{summary}"},
            ])

            try:
                parsed = extract_json_object(raw_output)
                review = SecurityLLMReviewResult.model_validate(parsed)
            except (ValueError, ValidationError) as parse_error:
                logger.warning(
                    "Security Agent LLM review layer returned unparseable output, skipping: %s",
                    parse_error,
                )
                return (
                    f"Skipped -- LLM response could not be parsed as the expected findings JSON "
                    f"({type(parse_error).__name__}). The deterministic layers above are "
                    f"unaffected and are this report's evidence.",
                    [],
                )

            llm_findings = [
                {
                    "id": f"SEC-LLM:{index}",
                    "rule_id": "SEC-LLM-REVIEW",
                    "layer": "llm",
                    "severity": item.severity,
                    "cwe": item.cwe or "N/A",
                    "file": item.file,
                    "line": item.line,
                    "message": (
                        f"{item.title} -- {item.description} "
                        f"Recommendation: {item.recommendation}"
                    ).strip(),
                }
                for index, item in enumerate(review.additional_findings, start=1)
            ]

            status = f"LLM review layer ran successfully: {len(llm_findings)} additional finding(s)."
            if review.notes:
                status += f" Notes: {review.notes}"
            return status, llm_findings
        except Exception as error:  # noqa: BLE001 -- an unreachable LLM must not fail the whole scan
            logger.warning("Security Agent LLM review layer unavailable, skipping: %s", error)
            return (
                f"Skipped -- LLM provider unreachable in this run ({type(error).__name__}). "
                f"The three deterministic layers above (pattern, secret, dependency) are "
                f"unaffected and are this report's evidence.",
                [],
            )


security_agent = SecurityAgent()
