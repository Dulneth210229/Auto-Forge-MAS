"""
Test execution for the QA Agent.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from app.agents.qa_agent.schemas import ExecutionResult

logger = logging.getLogger(__name__)


class TestExecutor:
    """
    Executes generated test files and collects execution results.

    Currently supports:
        - pytest (.py)
        - Jest (.js/.jsx/.ts/.tsx)
    """

    def execute(
        self,
        tests_directory: Path,
    ) -> ExecutionResult:

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

        #
        # ---------------------------------------------------------
        # Detect test frameworks
        # ---------------------------------------------------------
        #

        python_tests = list(
            tests_directory.glob("test_*.py")
        )

        jest_tests = []

        for pattern in (
            "*.test.js",
            "*.test.jsx",
            "*.test.ts",
            "*.test.tsx",
        ):
            jest_tests.extend(
                tests_directory.glob(pattern)
            )

        logger.info(
            "Detected %d pytest tests and %d Jest tests.",
            len(python_tests),
            len(jest_tests),
        )

        #
        # ---------------------------------------------------------
        # No tests
        # ---------------------------------------------------------
        #

        if not python_tests and not jest_tests:

            logger.warning(
                "No executable test files found."
            )

            return ExecutionResult(
                success=True,
                exit_code=0,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                duration_seconds=0.0,
                stdout="No executable tests found.",
                stderr="",
            )

        #
        # ---------------------------------------------------------
        # Execute pytest
        # ---------------------------------------------------------
        #

        python_result = ExecutionResult(
            success=True,
            exit_code=0,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            duration_seconds=0.0,
            stdout="",
            stderr="",
        )

        if python_tests:

            python_result = self._run_pytest(
                tests_directory
            )

        #
        # ---------------------------------------------------------
        # Execute Jest
        # ---------------------------------------------------------
        #

        jest_result = ExecutionResult(
            success=True,
            exit_code=0,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            duration_seconds=0.0,
            stdout="",
            stderr="",
        )

        if jest_tests:

            logger.info(
                "Executing Jest tests..."
            )

            jest_result = self._run_jest(
                tests_directory,
            )

        #
        # ---------------------------------------------------------
        # Aggregate results
        # ---------------------------------------------------------
        #

        total_tests = (
            (python_result.total_tests or 0)
            + (jest_result.total_tests or 0)
        )

        passed = (
            (python_result.passed or 0)
            + (jest_result.passed or 0)
        )

        failed = (
            (python_result.failed or 0)
            + (jest_result.failed or 0)
        )

        skipped = (
            (python_result.skipped or 0)
            + (jest_result.skipped or 0)
        )

        stdout = (python_result.stdout or "")

        if jest_result.stdout:
            stdout += "\n\n" + jest_result.stdout

        stderr = (python_result.stderr or "")

        if jest_result.stderr:
            stderr += "\n\n" + jest_result.stderr

        success = failed == 0

        logger.info(
            "Execution Summary: "
            "Total=%d Passed=%d Failed=%d Skipped=%d",
            total_tests,
            passed,
            failed,
            skipped,
        )

        return ExecutionResult(
            success=success,
            exit_code=(
                jest_result.exit_code
                if jest_tests
                else python_result.exit_code
            ),
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_seconds=(
                (python_result.duration_seconds or 0.0)
                + (jest_result.duration_seconds or 0.0)
            ),
            stdout=stdout,
            stderr=stderr,
        )

    # -------------------------------------------------------------
    # Pytest
    # -------------------------------------------------------------

    def _run_pytest(
        self,
        tests_directory: Path,
    ) -> ExecutionResult:

        logger.info(
            "Executing pytest..."
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

            duration = (
                time.perf_counter()
                - start_time
            )

            stdout = process.stdout or ""

            stderr = process.stderr or ""

            (
                total,
                passed,
                failed,
                skipped,
            ) = self._parse_pytest_output(
                stdout
            )

            logger.info(
                "Pytest finished. "
                "Passed=%d Failed=%d Skipped=%d",
                passed,
                failed,
                skipped,
            )

            return ExecutionResult(
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

        except Exception as ex:

            logger.exception(
                "Error executing pytest."
            )

            return ExecutionResult(
                success=False,
                exit_code=-1,
                duration_seconds=0.0,
                stdout="",
                stderr=str(ex),
            )

    # -------------------------------------------------------------
    # Jest
    # -------------------------------------------------------------

    def _run_jest(
        self,
        tests_directory: Path,
    ) -> ExecutionResult:

        logger.info(
            "Executing Jest..."
        )

        npx = shutil.which("npx.cmd") or shutil.which("npx")

        logger.info("PATH: %s", os.environ.get("PATH"))
        logger.info("Resolved npx: %s", npx)
        logger.info("Resolved node: %s", shutil.which("node"))

        if npx is None:
            raise FileNotFoundError(
                "Unable to locate npx. Ensure Node.js is installed and available in PATH."
            )

        command = [
            npx,
            "jest",
            tests_directory.name,
            "--runInBand",
            "--json",
            "--passWithNoTests",
        ]

        logger.info("Running command: %s", command)
        logger.info("Working directory: %s", tests_directory.parent)

        start_time = time.perf_counter()

        try:

            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=tests_directory.parent,
            )

            duration = (
                time.perf_counter()
                - start_time
            )

            stdout = process.stdout or ""
            stderr = process.stderr or ""

            logger.info("Jest raw stdout:\n%s", stdout)

            try:
                # --- Improved JSON extraction ---
                json_start = stdout.find("{")
                json_end = stdout.rfind("}")

                if json_start == -1 or json_end == -1:
                    raise json.JSONDecodeError(
                        "No JSON found",
                        stdout,
                        0,
                    )

                json_str = stdout[
                    json_start:json_end + 1
                ]

                result = json.loads(json_str)

                total = result.get("numTotalTests", 0)
                passed = result.get("numPassedTests", 0)
                failed = result.get("numFailedTests", 0)
                skipped = result.get("numPendingTests", 0)

                return ExecutionResult(
                    success=result.get("success", False),
                    exit_code=process.returncode,
                    total_tests=total,
                    passed=passed,
                    failed=failed,
                    skipped=skipped,
                    duration_seconds=duration,
                    stdout=stdout,
                    stderr=stderr,
                )

            except json.JSONDecodeError:

                logger.error(
                    "Failed to parse Jest JSON output."
                )

                return ExecutionResult(
                    success=False,
                    exit_code=process.returncode,
                    total_tests=0,
                    passed=0,
                    failed=0,
                    skipped=0,
                    duration_seconds=duration,
                    stdout=stdout,
                    stderr=stderr,
                )

        except Exception as ex:

            logger.exception(
                "Error executing Jest."
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
            passed = int(
                passed_match.group(1)
            )

        if failed_match:
            failed = int(
                failed_match.group(1)
            )

        if skipped_match:
            skipped = int(
                skipped_match.group(1)
            )

        total = (
            passed
            + failed
            + skipped
        )

        return (
            total,
            passed,
            failed,
            skipped,
        )


test_executor = TestExecutor()