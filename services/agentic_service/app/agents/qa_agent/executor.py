"""
Test execution for the QA Agent.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from pathlib import Path

from app.agents.qa_agent.schemas import ExecutionResult

logger = logging.getLogger(__name__)


class TestExecutor:
    """
    Executes generated pytest test files and collects execution results.
    """

    def execute(
        self,
        tests_directory: Path,
    ) -> ExecutionResult:
        """
        Execute all generated pytest tests.

        Args:
            tests_directory:
                Directory containing generated test files.

        Returns:
            ExecutionResult
        """

        logger.info(
            "Executing generated tests from %s",
            tests_directory,
        )

        if not tests_directory.exists():

            logger.warning(
                "Generated tests directory does not exist."
            )

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stderr="Generated tests directory not found.",
            )

        command = [
            "pytest",
            str(tests_directory),
            "-q",
        ]

        start_time = time.perf_counter()

        try:

            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=tests_directory.parent,
            )

            duration = time.perf_counter() - start_time

            stdout = process.stdout or ""
            stderr = process.stderr or ""

            (
                total,
                passed,
                failed,
                skipped,
            ) = self._parse_pytest_output(stdout)

            result = ExecutionResult(
                success=process.returncode == 0,
                exit_code=process.returncode,
                total_tests=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration_seconds=duration,
                stdout=stdout,
                stderr=stderr,
            )

            logger.info(
                "Pytest finished. Passed=%d Failed=%d Skipped=%d",
                passed,
                failed,
                skipped,
            )

            return result

        except Exception as ex:

            logger.exception(
                "Error executing generated tests."
            )

            return ExecutionResult(
                success=False,
                exit_code=-1,
                duration_seconds=0.0,
                stdout="",
                stderr=str(ex),
            )

    # -------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------

    def _parse_pytest_output(
        self,
        stdout: str,
    ) -> tuple[int, int, int, int]:
        """
        Parse pytest summary output.

        Example:

        3 passed in 2.12s

        2 passed, 1 failed in 1.54s

        4 passed, 2 skipped in 3.11s
        """

        passed = 0
        failed = 0
        skipped = 0

        passed_match = re.search(
            r"(\d+)\s+passed",
            stdout,
        )

        failed_match = re.search(
            r"(\d+)\s+failed",
            stdout,
        )

        skipped_match = re.search(
            r"(\d+)\s+skipped",
            stdout,
        )

        if passed_match:
            passed = int(passed_match.group(1))

        if failed_match:
            failed = int(failed_match.group(1))

        if skipped_match:
            skipped = int(skipped_match.group(1))

        total = passed + failed + skipped

        return (
            total,
            passed,
            failed,
            skipped,
        )


test_executor = TestExecutor()