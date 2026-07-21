"""
Markdown builder for the QA Agent.
"""

from __future__ import annotations

from app.agents.qa_agent.schemas import QAReport


class QAMarkdownBuilder:
    """
    Builds a human-readable QA report in Markdown format.
    """

    @staticmethod
    def build(
        project_name: str,
        feature_name: str,
        report: QAReport,
    ) -> str:
        """
        Build a Markdown QA report.
        """

        lines: list[str] = []

        lines.append("# QA Report")
        lines.append("")
        lines.append(f"**Project:** {project_name}")
        lines.append(f"**Feature:** {feature_name}")
        lines.append(f"**Generated:** {report.generated_at}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Total Tests: {report.summary.total_tests}")
        lines.append(f"- Passed: {report.summary.passed}")
        lines.append(f"- Failed: {report.summary.failed}")
        lines.append(f"- Skipped: {report.summary.skipped}")
        lines.append(f"- Pass Rate: {report.summary.pass_rate:.2f}%")
        lines.append(f"- Status: {report.summary.status}")
        lines.append("")

        lines.append("## Metrics")
        lines.append("")
        lines.append(
            f"- Generated Test Files: {report.metrics.generated_test_files}"
        )
        lines.append(
            f"- Generation Time: {report.metrics.generation_time_seconds:.2f} seconds"
        )
        lines.append(
            f"- Execution Time: {report.metrics.execution_time_seconds:.2f} seconds"
        )
        lines.append(
            f"- Total Duration: {report.metrics.total_duration_seconds:.2f} seconds"
        )
        lines.append("")

        lines.append("## Findings")
        lines.append("")

        if not report.findings:
            lines.append("No QA findings were detected.")
            lines.append("")
        else:
            for index, finding in enumerate(report.findings, start=1):
                lines.append(f"### Finding {index}")
                lines.append(f"- **Title:** {finding.title}")
                lines.append(f"- **Severity:** {finding.severity}")

                if finding.file:
                    lines.append(f"- **File:** {finding.file}")

                if finding.line is not None:
                    lines.append(f"- **Line:** {finding.line}")

                lines.append(f"- **Description:** {finding.description}")
                lines.append(
                    f"- **Recommendation:** {finding.recommendation}"
                )
                lines.append(
                    f"- **Confidence:** {finding.confidence:.2f}"
                )
                lines.append("")

        return "\n".join(lines)