"""
Patch Service.

This service applies patch-based file changes to the generated MERN workspace.

Important idea:
Agents should NOT directly write random files.

Correct flow:
    Agent produces structured patch request
        -> patch_service validates patch action
        -> code_file_service writes safely inside workspace
        -> codebase_manifest_service records file ownership
        -> patch_service records patch history

For MVP, we can still write full file content internally, but every change
must be recorded as a patch.

Patch history is stored at:

memory/{project_slug}/features/{feature_slug}/patch_history.json

Later, UI/UX Agent and Coder Agent can also copy the patch records into:
outputs/{project_slug}/{feature_slug}/04_uiux/frontend_patch_log_v1.json
outputs/{project_slug}/{feature_slug}/05_code/project_patch_log_v1.json
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.code_file_service import code_file_service
from app.services.codebase_manifest_service import codebase_manifest_service
from app.services.project_memory_service import project_memory_service
from app.utils.file_manager import ensure_directory, read_json_file, write_json_file
from app.utils.id_generator import generate_id


class PatchService:
    """
    Applies and records safe patch-based file changes.
    """

    ALLOWED_PATCH_ACTIONS = {
        "create_directory",
        "create_file",
        "modify_file",
        "append_to_file",
        "replace_section",
        "update_json_field",
    }

    # delete_file is intentionally not allowed for MVP.
    # It can be added later only with explicit human approval.

    def get_patch_history_path(self, project: dict[str, Any], feature: dict[str, Any],) -> Path:
        """
        Return patch history file path for a feature.

        memory/{project_slug}/features/{feature_slug}/patch_history.json
        """
        feature_dir = project_memory_service.get_feature_memory_dir(
            project_name=project["project_name"],
            feature_name=feature["feature_name"],
        )
        ensure_directory(feature_dir)

        return feature_dir / "patch_history.json"

    def initialize_patch_history(self, project: dict[str, Any], feature: dict[str, Any],) -> dict[str, Any]:
        """
        Create patch_history.json if it does not exist.
        """
        path = self.get_patch_history_path(project, feature)

        if not path.exists():
            patch_history = {
                "project_id": project["project_id"],
                "feature_id": feature["feature_id"],
                "created_at": self._now(),
                "last_updated": self._now(),
                "patches": [],
            }
            write_json_file(path, patch_history)

        return read_json_file(path)

    def read_patch_history(self, project: dict[str, Any], feature: dict[str, Any],) -> dict[str, Any]:
        """
        Read patch history.
        """
        return self.initialize_patch_history(project, feature)

    def apply_patch(self, project: dict[str, Any], feature: dict[str, Any], patch: dict[str, Any], agent_name: str, workspace: str = "staging",) -> dict[str, Any]:
        """
        Apply one patch safely.

        Expected patch shape:

        {
            "task_id": "LOGIN-FE-001",
            "file_path": "frontend/src/pages/Login.jsx",
            "change_type": "create_file",
            "content": "...",
            "description": "Created Login page UI",
            "purpose": "Login page component"
        }

        Supported change_type:
        - create_directory
        - create_file
        - modify_file
        - append_to_file
        - replace_section
        - update_json_field
        """
        change_type = patch.get("change_type")
        file_path = patch.get("file_path")

        if change_type not in self.ALLOWED_PATCH_ACTIONS:
            raise ValueError(f"Unsupported patch change_type: {change_type}")

        if not file_path:
            raise ValueError("Patch file_path is required.")

        patch_id = patch.get("patch_id") or generate_id("patch")

        result: dict[str, Any] = {
            "patch_id": patch_id,
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "task_id": patch.get("task_id"),
            "agent_name": agent_name,
            "file_path": file_path,
            "change_type": change_type,
            "description": patch.get("description", ""),
            "purpose": patch.get("purpose", ""),
            "workspace": workspace,
            "status": "pending",
            "error_message": None,
            "created_at": self._now(),
            "applied_at": None,
        }

        try:
            if change_type == "create_directory":
                self._apply_create_directory(project, file_path, workspace)

            elif change_type in {"create_file", "modify_file"}:
                self._apply_write_file(
                    project=project,
                    file_path=file_path,
                    content=patch.get("content", ""),
                    workspace=workspace,
                    overwrite=True,
                )

            elif change_type == "append_to_file":
                self._apply_append_file(
                    project=project,
                    file_path=file_path,
                    content=patch.get("content", ""),
                    workspace=workspace,
                )

            elif change_type == "replace_section":
                self._apply_replace_section(
                    project=project,
                    file_path=file_path,
                    old_text=patch.get("old_text", ""),
                    new_text=patch.get("new_text", ""),
                    workspace=workspace,
                )

            elif change_type == "update_json_field":
                self._apply_update_json_field(
                    project=project,
                    file_path=file_path,
                    json_path=patch.get("json_path", ""),
                    value=patch.get("value"),
                    workspace=workspace,
                )

            result["status"] = "applied"
            result["applied_at"] = self._now()

            # Register or update file in the project file manifest.
            # This is useful later for Coder Agent and merge logic.
            if change_type != "create_directory":
                codebase_manifest_service.register_file(
                    project=project,
                    file_path=file_path,
                    feature_id=feature["feature_id"],
                    created_by=agent_name,
                    last_modified_by=agent_name,
                    purpose=patch.get("purpose", patch.get("description", "")),
                )

        except Exception as exc:
            result["status"] = "failed"
            result["error_message"] = str(exc)

        self._record_patch(project, feature, result)

        if result["status"] == "failed":
            raise RuntimeError(result["error_message"])

        return result

    def apply_patches(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        patches: list[dict[str, Any]],
        agent_name: str,
        workspace: str = "staging",
    ) -> list[dict[str, Any]]:
        """
        Apply multiple patches one by one.

        If one patch fails, the exception will stop the current task.
        This is safer than silently continuing.
        """
        applied_results = []

        for patch in patches:
            result = self.apply_patch(
                project=project,
                feature=feature,
                patch=patch,
                agent_name=agent_name,
                workspace=workspace,
            )
            applied_results.append(result)

        return applied_results

    # ------------------------------------------------------------------
    # Patch action implementations
    # ------------------------------------------------------------------

    def _apply_create_directory(self, project: dict[str, Any], file_path: str, workspace: str,) -> None:
        """
        Create directory inside workspace.

        Example:
            frontend/src/components/auth
        """
        code_file_service.create_workspace_directory(
            project=project,
            relative_path=file_path,
            workspace=workspace,
        )

    def _apply_write_file(
        self,
        project: dict[str, Any],
        file_path: str,
        content: str,
        workspace: str,
        overwrite: bool,
    ) -> None:
        """
        Create or modify a file.
        """
        if not isinstance(content, str):
            raise ValueError("Patch content must be a string.")

        code_file_service.write_workspace_file(
            project=project,
            relative_path=file_path,
            content=content,
            workspace=workspace,
            overwrite=overwrite,
        )

    def _apply_append_file(self, project: dict[str, Any], file_path: str, content: str, workspace: str,) -> None:
        """
        Append content to a file.
        """
        if not isinstance(content, str):
            raise ValueError("Patch content must be a string.")

        code_file_service.append_workspace_file(
            project=project,
            relative_path=file_path,
            content=content,
            workspace=workspace,
        )

    def _apply_replace_section(
        self,
        project: dict[str, Any],
        file_path: str,
        old_text: str,
        new_text: str,
        workspace: str,
    ) -> None:
        """
        Replace a specific text section in a file.

        This is safer than rewriting the whole file when only one section changes.
        """
        if not old_text:
            raise ValueError("replace_section requires old_text.")

        current_content = code_file_service.read_workspace_file(
            project=project,
            relative_path=file_path,
            workspace=workspace,
        )

        if old_text not in current_content:
            raise ValueError(f"old_text was not found in file: {file_path}")

        updated_content = current_content.replace(old_text, new_text, 1)

        code_file_service.write_workspace_file(
            project=project,
            relative_path=file_path,
            content=updated_content,
            workspace=workspace,
            overwrite=True,
        )

    def _apply_update_json_field(
        self,
        project: dict[str, Any],
        file_path: str,
        json_path: str,
        value: Any,
        workspace: str,
    ) -> None:
        """
        Update a top-level JSON field.

        MVP version:
        - supports only top-level JSON fields.
        - example json_path: "scripts"

        Later, we can support nested paths like:
            scripts.dev
        """
        if not json_path:
            raise ValueError("update_json_field requires json_path.")

        current_content = code_file_service.read_workspace_file(
            project=project,
            relative_path=file_path,
            workspace=workspace,
        )

        import json

        try:
            data = json.loads(current_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON file: {file_path}") from exc

        data[json_path] = value

        updated_content = json.dumps(data, indent=2)

        code_file_service.write_workspace_file(
            project=project,
            relative_path=file_path,
            content=updated_content,
            workspace=workspace,
            overwrite=True,
        )

    # ------------------------------------------------------------------
    # Patch history
    # ------------------------------------------------------------------

    def _record_patch(self, project: dict[str, Any], feature: dict[str, Any], patch_record: dict[str, Any],) -> None:
        """
        Save patch record to patch_history.json.
        """
        history = self.initialize_patch_history(project, feature)

        history["patches"].append(patch_record)
        history["last_updated"] = self._now()

        write_json_file(
            self.get_patch_history_path(project, feature),
            history,
        )

    def _now(self) -> str:
        """
        Return UTC timestamp string.
        """
        return datetime.utcnow().isoformat() + "Z"


patch_service = PatchService()