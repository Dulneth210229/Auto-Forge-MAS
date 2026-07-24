"""
QA test validator.

Validates generated test cases before they are saved
or executed.

Validation checks:
- Empty file
- Python syntax (Python only)
- Test structure (Python only)
- File naming convention
- Duplicate test functions (Python only)
"""

from __future__ import annotations

import ast
import re

from app.agents.qa_agent.schemas import ValidationResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TestValidator:
    """
    Validates generated test files.
    """

    PYTHON_EXTENSIONS = {".py"}

    def validate(
        self,
        filename: str,
        code: str,
        file_extension: str,
    ) -> ValidationResult:
        """
        Validate a generated test file.
        """

        result = ValidationResult()

        self._validate_empty(
            code=code,
            result=result,
        )

        if not result.valid:
            logger.warning(
                "Validation failed: generated test is empty."
            )
            return result

        self._validate_filename(
            filename=filename,
            result=result,
        )

        extension = file_extension.lower()

        if extension in self.PYTHON_EXTENSIONS:

            tree = self._validate_syntax(
                filename=filename,
                code=code,
                result=result,
            )

            if tree is None:
                logger.warning(
                    "Validation failed: syntax error in %s",
                    filename,
                )
                return result

            self._validate_pytest_structure(
                tree=tree,
                result=result,
            )

            self._validate_duplicate_tests(
                tree=tree,
                result=result,
            )

        else:

            logger.info(
                "Skipping Python AST validation for %s files.",
                extension,
            )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_error(
        self,
        result: ValidationResult,
        message: str,
    ) -> None:
        """
        Add a validation error.
        """

        result.valid = False
        result.score = max(
            0,
            result.score - 25,
        )
        result.validation_errors.append(message)

    def _add_warning(
        self,
        result: ValidationResult,
        message: str,
    ) -> None:
        """
        Add a validation warning.
        """

        result.score = max(
            0,
            result.score - 5,
        )
        result.validation_warnings.append(message)

    # ------------------------------------------------------------------
    # Validation Rules
    # ------------------------------------------------------------------

    def _validate_empty(
        self,
        code: str,
        result: ValidationResult,
    ) -> None:
        """
        Ensure generated code is not empty.
        """

        if not code or not code.strip():
            self._add_error(
                result,
                "Generated test is empty.",
            )

    def _validate_syntax(
        self,
        filename: str,
        code: str,
        result: ValidationResult,
    ) -> ast.AST | None:
        """
        Validate Python syntax.
        """

        try:
            return ast.parse(
                code,
                filename=filename,
            )

        except SyntaxError as ex:

            self._add_error(
                result,
                f"Syntax error: {ex.msg} (line {ex.lineno})",
            )

            return None

    def _validate_filename(
        self,
        filename: str,
        result: ValidationResult,
    ) -> None:
        """
        Ensure test naming convention.
        """

        if not filename.startswith("test_"):

            self._add_warning(
                result,
                "Filename should start with 'test_'.",
            )

    def _validate_pytest_structure(
        self,
        tree: ast.AST,
        result: ValidationResult,
    ) -> None:
        """
        Ensure at least one pytest test exists.
        """

        test_count = 0

        for node in ast.walk(tree):

            if (
                isinstance(node, ast.FunctionDef)
                and node.name.startswith("test_")
            ):
                test_count += 1

            elif (
                isinstance(node, ast.ClassDef)
                and node.name.startswith("Test")
            ):
                test_count += 1

        if test_count == 0:

            self._add_error(
                result,
                "No pytest test functions or test classes found.",
            )

    def _validate_duplicate_tests(
        self,
        tree: ast.AST,
        result: ValidationResult,
    ) -> None:
        """
        Detect duplicate pytest test function names.
        """

        names: set[str] = set()

        for node in ast.walk(tree):

            if (
                not isinstance(node, ast.FunctionDef)
                or not node.name.startswith("test_")
            ):
                continue

            if node.name in names:

                self._add_error(
                    result,
                    f"Duplicate test function '{node.name}'.",
                )

            names.add(node.name)


test_validator = TestValidator()