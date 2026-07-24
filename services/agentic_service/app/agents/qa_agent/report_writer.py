"""
QA report writer.

Serializes QA reports into JSON and Markdown formats.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.agents.qa_agent.schemas import QAReport

logger = logging.getLogger(__name__)


class QAReportWriter:
    """
    Writes QA reports to disk.
    """

    def write(
        self,
        report: QAReport,
        output_directory: Path,
    ) -> tuple[Path, Path]:
        """
        Write JSON and Markdown reports.

        Returns:
            (json_path, markdown_path)
        """

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        json_path = output_directory / "qa_report.json"
        markdown_path = output_directory / "qa_report.md"

        self._write_json(
            report,
            json_path,
        )

        self._write_markdown(
            report,
            markdown_path,
        )

        logger.info(
            "QA report written successfully."
        )

        return (
            json_path,
            markdown_path,
        )

    # ---------------------------------------------------------
    # JSON
    # ---------------------------------------------------------

    def _write_json(
        self,
        report: QAReport,
        output_file: Path,
    ) -> None:
        """
        Write report as JSON.
        """

        output_file.write_text(
            json.dumps(
                report.model_dump(
                    mode="json",
                ),
                indent=4,
            ),
            encoding="utf-8",
        )

    # ---------------------------------------------------------
    # Markdown
    # ---------------------------------------------------------

    def _write_markdown(
        self,
        report: QAReport,
        output_file: Path,
    ) -> None:
        """
        Write report as Markdown.
        """

        lines: list[str] = []

        lines.append("# QA Report")
        lines.append("")

        lines.append(f"**Feature ID:** {report.feature_id}")
        lines.append(f"**Generated:** {report.generated_at}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")

        summary = report.summary

        lines.append(f"- Status: **{summary.status}**")
        lines.append(f"- Total Tests: {summary.total_tests}")
        lines.append(f"- Passed: {summary.passed}")
        lines.append(f"- Failed: {summary.failed}")
        lines.append(f"- Skipped: {summary.skipped}")
        lines.append(f"- Pass Rate: {summary.pass_rate:.2f}%")
        lines.append("")

        lines.append("## Metrics")
        lines.append("")

        metrics = report.metrics

        lines.append(
            f"- Generated Test Files: {metrics.generated_test_files}"
        )

        lines.append(
            f"- Generation Time: {metrics.generation_time_seconds:.2f}s"
        )

        lines.append(
            f"- Execution Time: {metrics.execution_time_seconds:.2f}s"
        )

        lines.append(
            f"- Total Duration: {metrics.total_duration_seconds:.2f}s"
        )

        lines.append("")

        lines.append("## Findings")
        lines.append("")

        if not report.findings:

            lines.append("No findings.")
            lines.append("")

        else:

            for finding in report.findings:

                lines.append(
                    f"### {finding.title}"
                )

                lines.append(
                    f"- Severity: **{finding.severity}**"
                )

                if finding.file:

                    lines.append(
                        f"- File: `{finding.file}`"
                    )

                if finding.line is not None:

                    lines.append(
                        f"- Line: {finding.line}"
                    )

                lines.append(
                    f"- Description: {finding.description}"
                )

                lines.append(
                    f"- Recommendation: {finding.recommendation}"
                )

                lines.append(
                    f"- Confidence: {finding.confidence:.2f}"
                )

                lines.append("")

        output_file.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )


qa_report_writer = QAReportWriter()