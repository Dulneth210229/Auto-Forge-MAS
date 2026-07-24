"""
Workspace test generation for the QA Agent.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from app.agents.qa_agent.llm_generator import LLMTestGenerator
from app.agents.qa_agent.schemas import GeneratedTestFile
from app.agents.qa_agent.validator import test_validator

logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "outputs",
    "generated_tests",
    "dist",
    "build",
}


class TestGenerator:
    """
    Generates functional test code for a project workspace.

    Responsibilities:
    - Collect source files
    - Generate tests using the LLM
    - Validate generated tests
    - Return generated test results

    Saving generated tests is handled by the QA Agent through
    the ArtifactService.
    """

    def __init__(self):
        self.llm_generator = LLMTestGenerator()

    # ------------------------------------------------------------------
    # Collect source files
    # ------------------------------------------------------------------

    def collect_source_files(
        self,
        workspace: Path,
    ) -> List[Path]:
        """
        Collect supported source files from the workspace.
        """

        logger.info("Scanning workspace: %s", workspace)

        source_files: List[Path] = []

        for file in workspace.rglob("*"):

            if not file.is_file():
                continue

            if any(
                part in IGNORED_DIRECTORIES
                for part in file.parts
            ):
                continue

            if file.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            source_files.append(file)

        source_files.sort()

        logger.info(
            "Found %d supported source files.",
            len(source_files),
        )

        return source_files

    # ------------------------------------------------------------------
    # Generate tests
    # ------------------------------------------------------------------

    async def generate_tests(
        self,
        workspace: Path,
    ) -> List[GeneratedTestFile]:
        """
        Generate and validate test code for every supported source file.

        This method does NOT save files.
        The QA Agent is responsible for artifact creation.
        """

        generated_files: List[GeneratedTestFile] = []

        source_files = self.collect_source_files(workspace)

        for source_file in source_files:

            logger.info(
                "Generating tests for %s",
                source_file,
            )

            try:

                source_code = source_file.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                generated_test = await self.llm_generator.generate_tests(
                    source_code
                )

                validation = test_validator.validate(
                    filename=f"test_{source_file.stem}.py",
                    code=generated_test,
                )

                # ------------------------------------------------------
                # Validation failed
                # ------------------------------------------------------

                if not validation.valid:

                    logger.warning(
                        "Generated test failed validation for %s",
                        source_file,
                    )

                    for error in validation.validation_errors:
                        logger.warning(
                            "Validation Error: %s",
                            error,
                        )

                    generated_files.append(
                        GeneratedTestFile(
                            source_file=str(source_file),
                            test_file=f"test_{source_file.stem}.py",
                            generated_code=None,
                            status="FAILED",
                            error="; ".join(
                                validation.validation_errors
                            ),
                            validation_score=validation.score,
                            validation_errors=validation.validation_errors,
                            validation_warnings=validation.validation_warnings,
                        )
                    )

                    continue

                # ------------------------------------------------------
                # Validation warnings
                # ------------------------------------------------------

                for warning in validation.validation_warnings:

                    logger.warning(
                        "Validation Warning (%s): %s",
                        source_file.name,
                        warning,
                    )

                # ------------------------------------------------------
                # Validation succeeded
                # ------------------------------------------------------

                generated_files.append(
                    GeneratedTestFile(
                        source_file=str(source_file),
                        test_file=f"test_{source_file.stem}.py",
                        generated_code=generated_test,
                        status="SUCCESS",
                        validation_score=validation.score,
                        validation_errors=validation.validation_errors,
                        validation_warnings=validation.validation_warnings,
                    )
                )

            except Exception as exc:

                logger.exception(
                    "Failed generating tests for %s",
                    source_file,
                )

                generated_files.append(
                    GeneratedTestFile(
                        source_file=str(source_file),
                        test_file=f"test_{source_file.stem}.py",
                        generated_code=None,
                        status="FAILED",
                        error=str(exc),
                        validation_score=0,
                        validation_errors=[str(exc)],
                        validation_warnings=[],
                    )
                )

        success_count = sum(
            1
            for file in generated_files
            if file.status == "SUCCESS"
        )

        failure_count = sum(
            1
            for file in generated_files
            if file.status == "FAILED"
        )

        logger.info(
            "QA generation completed. Success=%d Failed=%d",
            success_count,
            failure_count,
        )

        return generated_files