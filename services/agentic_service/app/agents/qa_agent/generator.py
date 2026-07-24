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
    - Save validated tests into workspace/generated_tests
    - Return generated test results

    Saving generated tests as project artifacts is handled
    by the QA Agent through the ArtifactService.
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
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_test_filename(
        source_file: Path,
    ) -> str:
        """
        Build the generated test filename according
        to the source language.
        """

        extension = source_file.suffix.lower()

        if extension == ".py":
            return f"test_{source_file.stem}.py"

        return f"{source_file.stem}.test{extension}"

    # ------------------------------------------------------------------
    # Generate tests
    # ------------------------------------------------------------------

    async def generate_tests(
        self,
        workspace: Path,
    ) -> List[GeneratedTestFile]:
        """
        Generate, validate and save test code for every supported source file.
        """

        generated_files: List[GeneratedTestFile] = []

        source_files = self.collect_source_files(workspace)

        generated_tests_dir = workspace / "generated_tests"
        generated_tests_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            "Generated tests directory: %s",
            generated_tests_dir,
        )

        for source_file in source_files:

            logger.info(
                "Generating tests for %s",
                source_file,
            )

            test_filename = self._build_test_filename(
                source_file
            )

            try:

                source_code = source_file.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                generated_test = await self.llm_generator.generate_tests(
                    source_code=source_code,
                    file_extension=source_file.suffix,
                )

                validation = test_validator.validate(
                    filename=test_filename,
                    code=generated_test,
                    file_extension=source_file.suffix,
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
                            test_file=test_filename,
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
                # Save generated test
                # ------------------------------------------------------

                output_file = generated_tests_dir / test_filename

                output_file.write_text(
                    generated_test,
                    encoding="utf-8",
                )

                logger.info(
                    "Saved generated test: %s",
                    output_file,
                )

                # ------------------------------------------------------
                # Validation succeeded
                # ------------------------------------------------------

                generated_files.append(
                    GeneratedTestFile(
                        source_file=str(source_file),
                        test_file=test_filename,
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
                        test_file=test_filename,
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