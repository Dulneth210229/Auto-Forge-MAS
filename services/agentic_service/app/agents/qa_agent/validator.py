"""
QA test validator.

Validates generated test cases before they are saved
or executed.

Validation checks:
- Empty file
- Python syntax
- Pytest structure
- File naming convention
- Duplicate test functions
"""

from __future__ import annotations

import ast
import re

from app.agents.qa_agent.schemas import ValidationResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TestValidator:
    """
    Validates generated pytest test files.
    """

    def validate(
        self,
        filename: str,
        code: str,
    ) -> ValidationResult:
        """
        Validate a generated test file.
        """

        result = ValidationResult()

        self._validate_empty(code, result)

        if not result.valid:
            logger.warning("Validation failed: generated test is empty.")
            return result

        tree = self._validate_syntax(
            filename=filename,
            code=code,
            result=result,
        )

        if tree is None:
            logger.warning("Validation failed: syntax error in %s", filename)
            return result

        self._validate_filename(
            filename=filename,
            result=result,
        )

        self._validate_pytest_structure(
            tree=tree,
            result=result,
        )

        self._validate_duplicate_tests(
            tree=tree,
            result=result,
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
        result.score = max(0, result.score - 25)
        result.validation_errors.append(message)

    def _add_warning(
        self,
        result: ValidationResult,
        message: str,
    ) -> None:
        """
        Add a validation warning.
        """

        result.score = max(0, result.score - 5)
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
            return ast.parse(code, filename=filename)

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
        Ensure pytest naming convention.
        """

        if not re.match(r"^test_.*\.py$", filename):
            self._add_warning(
                result,
                "Filename does not follow pytest naming convention "
                "(expected test_<name>.py).",
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

            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    test_count += 1

            elif isinstance(node, ast.ClassDef):
                if node.name.startswith("Test"):
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

            if not isinstance(node, ast.FunctionDef):
                continue

            if not node.name.startswith("test_"):
                continue

            if node.name in names:
                self._add_error(
                    result,
                    f"Duplicate test function '{node.name}'.",
                )

            names.add(node.name)


test_validator = TestValidator()