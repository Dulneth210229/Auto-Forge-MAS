"""
Security Report Markdown Builder.
"""

from __future__ import annotations

from datetime import datetime


class SecurityMarkdownBuilder:
    """
    Builds a human-readable Security Report in Markdown format.
    """

    @staticmethod
    def build(
        project_name: str,
        feature_name: str,
        findings: list[dict],
        security_gate: dict,
    ) -> str:
        """
        Build the Markdown security report.

        Args:
            project_name: Project name.
            feature_name: Feature name.
            findings: Security findings.
            security_gate: Security gate evaluation.

        Returns:
            Markdown report.
        """

        report = []

        report.append("# Security Report")
        report.append("")
        report.append(f"**Project:** {project_name}")
        report.append(f"**Feature:** {feature_name}")
        report.append(f"**Generated:** {datetime.utcnow().isoformat()} UTC")
        report.append("")

        report.append("---")
        report.append("")

        report.append("## Security Gate")

        report.append(f"**Status:** {security_gate['status']}")
        report.append("")

        summary = security_gate["summary"]

        report.append("| Severity | Count |")
        report.append("|----------|------:|")
        report.append(f"| Critical | {summary['critical']} |")
        report.append(f"| High | {summary['high']} |")
        report.append(f"| Medium | {summary['medium']} |")
        report.append(f"| Low | {summary['low']} |")
        report.append(f"| Total | {summary['total_findings']} |")

        report.append("")
        report.append("---")
        report.append("")

        report.append("## Security Findings")
        report.append("")

        if not findings:

            report.append("No security findings were detected.")

        else:

            for index, finding in enumerate(findings, start=1):

                report.append(f"### {index}. {finding['title']}")
                report.append("")
                report.append(f"**Severity:** {finding['severity']}")
                report.append(f"**Description:** {finding['description']}")
                report.append(f"**Line:** {finding.get('line', 0)}")
                report.append(f"**CWE:** {finding.get('cwe', 'N/A')}")
                report.append(
                    f"**Recommendation:** {finding['recommendation']}"
                )
                report.append("")

        report.append("---")
        report.append("")
        report.append("*Generated automatically by the AutoForge Security Agent.*")

        return "\n".join(report)