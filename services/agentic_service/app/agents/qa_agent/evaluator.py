"""
QA evaluation module.

Builds the final QA report using generated test files
and execution results.
"""

from __future__ import annotations

import logging
from time import perf_counter

from app.agents.qa_agent.schemas import (
    ExecutionResult,
    GeneratedTestFile,
    QAFinding,
    QAMetrics,
    QAReport,
    QASummary,
)

logger = logging.getLogger(__name__)


class QAEvaluator:
    """
    Evaluates generated test files and execution results.
    """

    def evaluate(
        self,
        feature_id: str,
        generated_files: list[GeneratedTestFile],
        execution_result: ExecutionResult,
        generation_time: float = 0.0,
    ) -> QAReport:
        """
        Build the final QA report.
        """

        logger.info("Evaluating QA results...")

        start = perf_counter()

        findings = self._build_findings(
            generated_files,
            execution_result,
        )

        summary = self._build_summary(
            execution_result,
        )

        metrics = QAMetrics(
            generated_test_files=len(generated_files),
            generation_time_seconds=generation_time,
            execution_time_seconds=execution_result.duration_seconds,
            total_duration_seconds=(
                generation_time
                + execution_result.duration_seconds
            ),
        )

        report = QAReport(
            feature_id=feature_id,
            summary=summary,
            findings=findings,
            metrics=metrics,
        )

        logger.info(
            "QA evaluation completed in %.2f seconds.",
            perf_counter() - start,
        )

        return report

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------

    def _build_summary(
        self,
        execution: ExecutionResult,
    ) -> QASummary:
        """
        Build execution summary.
        """

        if execution.total_tests == 0:
            pass_rate = 0.0
        else:
            pass_rate = (
                execution.passed
                / execution.total_tests
            ) * 100

        # ✅ Updated status logic
        if execution.total_tests == 0:

            status = "GENERATED"

        elif execution.failed == 0:

            status = "PASSED"

        else:

            status = "FAILED"

        return QASummary(
            total_tests=execution.total_tests,
            passed=execution.passed,
            failed=execution.failed,
            skipped=execution.skipped,
            pass_rate=round(pass_rate, 2),
            status=status,
        )

    # -------------------------------------------------------------
    # Findings
    # -------------------------------------------------------------

    def _build_findings(
        self,
        generated_files: list[GeneratedTestFile],
        execution: ExecutionResult,
    ) -> list[QAFinding]:
        """
        Create QA findings.
        """

        findings: list[QAFinding] = []

        #
        # Generation failures
        #
        for generated in generated_files:

            if generated.status != "FAILED":
                continue

            findings.append(
                QAFinding(
                    title="Test Generation Failed",
                    description=generated.error
                    or "Unknown generation error.",
                    severity="High",
                    file=generated.source_file,
                    recommendation=(
                        "Review the source file and "
                        "regenerate the test."
                    ),
                    confidence=1.0,
                )
            )

        #
        # Execution failures
        #
        if execution.failed > 0:

            findings.append(
                QAFinding(
                    title="Test Execution Failed",
                    description=(
                        f"{execution.failed} test(s) failed "
                        "during execution."
                    ),
                    severity="Critical",
                    recommendation=(
                        "Review failed test cases and "
                        "fix the underlying implementation."
                    ),
                    confidence=1.0,
                )
            )

        #
        # Generated but not executed (updated logic)
        #
        if execution.total_tests == 0:

            findings.append(
                QAFinding(
                    title="Generated Tests Not Executed",
                    description=(
                        "Test files were successfully generated, "
                        "but no supported execution framework "
                        "was available."
                    ),
                    severity="Low",
                    recommendation=(
                        "Execute the generated tests using the "
                        "appropriate test framework (pytest or Jest)."
                    ),
                    confidence=1.0,
                )
            )

        return findings


qa_evaluator = QAEvaluator()