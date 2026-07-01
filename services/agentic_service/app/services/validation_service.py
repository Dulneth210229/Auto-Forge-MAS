"""
Validation Service.

This service performs lightweight validation after agent tasks.

Important:
This is not the future QA Agent.
This is only basic validation to catch obvious issues early.

For UI/UX Agent, validation checks:
- frontend files exist
- generated files are not empty
- Tailwind classes are present
- no backend files were modified
- task acceptance checks are listed

For Coder Agent later, validation can check:
- backend files exist
- package.json exists
- .env.example exists
- README exists
- basic JS syntax check through restricted command runner later
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.workspace_service import workspace_service
from app.services.code_file_service import code_file_service


class ValidationService:
    """
    Lightweight validation service for agent task outputs.
    """

    TAILWIND_HINTS = [
        "className=",
        "bg-",
        "text-",
        "flex",
        "grid",
        "rounded",
        "shadow",
        "p-",
        "m-",
        "w-",
        "h-",
    ]

    def validate_uiux_task_result(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        task: dict[str, Any],
        patch_results: list[dict[str, Any]],
        workspace: str = "staging",
    ) -> dict[str, Any]:
        """
        Validate one UI/UX task after patches were applied.

        This method is intentionally simple for MVP.
        Later, we can add Playwright rendering and screenshot checks.
        """
        checks: list[dict[str, Any]] = []

        checks.append(self._check_no_backend_files_modified(patch_results))
        checks.append(self._check_all_patches_applied(patch_results))

        expected_files = self._extract_expected_files(task)

        if expected_files:
            for file_path in expected_files:
                checks.append(
                    self._check_workspace_file_exists(
                        project=project,
                        file_path=file_path,
                        workspace=workspace,
                    )
                )

                if file_path.startswith("frontend/"):
                    checks.append(
                        self._check_file_not_empty(
                            project=project,
                            file_path=file_path,
                            workspace=workspace,
                        )
                    )

                    checks.append(
                        self._check_tailwind_or_react_present(
                            project=project,
                            file_path=file_path,
                            workspace=workspace,
                        )
                    )

        acceptance_checks = task.get("acceptance_checks", [])
        checks.append({
            "check_name": "acceptance_checks_present",
            "passed": bool(acceptance_checks),
            "message": (
                "Task includes acceptance checks."
                if acceptance_checks
                else "Task does not include acceptance checks."
            ),
        })

        passed = all(check["passed"] for check in checks)

        return {
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "task_id": task.get("task_id"),
            "agent_name": "uiux_agent",
            "validation_type": "uiux_task_result",
            "passed": passed,
            "checks": checks,
            "created_at": self._now(),
        }

    def validate_coder_task_result(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        task: dict[str, Any],
        patch_results: list[dict[str, Any]],
        workspace: str = "staging",
    ) -> dict[str, Any]:
        """
        Placeholder validation for Coder Agent.

        We add this now so the same validation service can support Coder Agent later.
        """
        checks: list[dict[str, Any]] = []

        checks.append(self._check_all_patches_applied(patch_results))

        expected_files = self._extract_expected_files(task)

        for file_path in expected_files:
            checks.append(
                self._check_workspace_file_exists(
                    project=project,
                    file_path=file_path,
                    workspace=workspace,
                )
            )

        passed = all(check["passed"] for check in checks)

        return {
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "task_id": task.get("task_id"),
            "agent_name": "coder_agent",
            "validation_type": "coder_task_result",
            "passed": passed,
            "checks": checks,
            "created_at": self._now(),
        }

    # ------------------------------------------------------------------
    # Common checks
    # ------------------------------------------------------------------

    def _check_all_patches_applied(self, patch_results: list[dict[str, Any]],) -> dict[str, Any]:
        """
        Check whether every patch was applied successfully.
        """
        failed_patches = [
            patch
            for patch in patch_results
            if patch.get("status") != "applied"
        ]

        return {
            "check_name": "all_patches_applied",
            "passed": len(failed_patches) == 0,
            "message": (
                "All patches were applied successfully."
                if not failed_patches
                else f"{len(failed_patches)} patch(es) failed."
            ),
            "failed_patch_ids": [
                patch.get("patch_id")
                for patch in failed_patches
            ],
        }

    def _check_no_backend_files_modified(self, patch_results: list[dict[str, Any]],) -> dict[str, Any]:
        """
        UI/UX Agent must not modify backend files.
        """
        backend_patches = [
            patch
            for patch in patch_results
            if str(patch.get("file_path", "")).startswith("backend/")
        ]

        return {
            "check_name": "uiux_no_backend_modification",
            "passed": len(backend_patches) == 0,
            "message": (
                "UI/UX Agent did not modify backend files."
                if not backend_patches
                else "UI/UX Agent attempted to modify backend files."
            ),
            "backend_patch_ids": [
                patch.get("patch_id")
                for patch in backend_patches
            ],
        }

    def _check_workspace_file_exists(self,project: dict[str, Any], file_path: str, workspace: str,) -> dict[str, Any]:
        """
        Check whether a file exists inside workspace.
        """
        try:
            absolute_path = workspace_service.resolve_workspace_path(
                project=project,
                relative_path=file_path,
                workspace=workspace,
            )

            exists = absolute_path.exists() and absolute_path.is_file()

            return {
                "check_name": "workspace_file_exists",
                "file_path": file_path,
                "passed": exists,
                "message": (
                    f"File exists: {file_path}"
                    if exists
                    else f"File missing: {file_path}"
                ),
            }

        except Exception as exc:
            return {
                "check_name": "workspace_file_exists",
                "file_path": file_path,
                "passed": False,
                "message": str(exc),
            }

    def _check_file_not_empty(
        self,
        project: dict[str, Any],
        file_path: str,
        workspace: str,
    ) -> dict[str, Any]:
        """
        Check whether a file has content.
        """
        try:
            content = code_file_service.read_workspace_file(
                project=project,
                relative_path=file_path,
                workspace=workspace,
            )

            passed = bool(content.strip())

            return {
                "check_name": "file_not_empty",
                "file_path": file_path,
                "passed": passed,
                "message": (
                    f"File is not empty: {file_path}"
                    if passed
                    else f"File is empty: {file_path}"
                ),
            }

        except Exception as exc:
            return {
                "check_name": "file_not_empty",
                "file_path": file_path,
                "passed": False,
                "message": str(exc),
            }

    def _check_tailwind_or_react_present(
        self,
        project: dict[str, Any],
        file_path: str,
        workspace: str,
    ) -> dict[str, Any]:
        """
        Basic check that generated frontend file looks like React/Tailwind.

        This is not a full compiler check.
        It only catches very obvious wrong outputs.
        """
        try:
            content = code_file_service.read_workspace_file(
                project=project,
                relative_path=file_path,
                workspace=workspace,
            )

            has_react_like_code = (
                "export default" in content
                or "function " in content
                or "const " in content
                or "return (" in content
            )

            has_tailwind_hint = any(
                hint in content
                for hint in self.TAILWIND_HINTS
            )

            passed = has_react_like_code and has_tailwind_hint

            return {
                "check_name": "react_tailwind_present",
                "file_path": file_path,
                "passed": passed,
                "message": (
                    "React-like structure and Tailwind-like classes found."
                    if passed
                    else "React-like structure or Tailwind-like classes missing."
                ),
            }

        except Exception as exc:
            return {
                "check_name": "react_tailwind_present",
                "file_path": file_path,
                "passed": False,
                "message": str(exc),
            }

    def _extract_expected_files(self, task: dict[str, Any],) -> list[str]:
        """
        Extract expected files from task definition.

        Supports common task keys:
        - files_to_create
        - files_to_modify
        - expected_files
        """
        files: list[str] = []

        for key in ["files_to_create", "files_to_modify", "expected_files"]:
            value = task.get(key, [])

            if isinstance(value, list):
                files.extend(value)

        # Remove duplicates while preserving order.
        seen = set()
        unique_files = []

        for file_path in files:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)

        return unique_files

    def _now(self) -> str:
        """
        Return UTC timestamp string.
        """
        return datetime.utcnow().isoformat() + "Z"


validation_service = ValidationService()