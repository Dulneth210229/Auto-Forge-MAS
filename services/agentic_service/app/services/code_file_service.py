"""
Code File Service.

This service safely creates, reads, and modifies files inside the generated
MERN project workspace.

Important:
Agents should not write files directly.

Correct flow:
    UI/UX Agent or Coder Agent
        -> patch_service
        -> code_file_service
        -> workspace file

Why:
- Prevent unsafe paths.
- Prevent accidental writes outside workspace.
- Keep file writing logic centralized.
- Make patch-based tracking easier.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.workspace_service import workspace_service
from app.utils.file_manager import ensure_directory, write_text_file, read_text_file


class CodeFileService:
    """
    Handles safe file operations inside project workspaces.
    """

    # ------------------------------------------------------------------
    # General workspace file operations
    # ------------------------------------------------------------------

    def write_workspace_file(self, project: dict[str, Any], relative_path: str, content: str, workspace: str = "staging", overwrite: bool = True,) -> str:
        """
        Write a file inside the selected workspace.

        Example:
            relative_path = "frontend/src/pages/Login.jsx"
            workspace = "staging"

        This writes:
            workspaces/{project_slug}/staging/frontend/src/pages/Login.jsx
        """
        workspace_service.prepare_staging_workspace(project)

        path = workspace_service.resolve_workspace_path(
            project=project,
            relative_path=relative_path,
            workspace=workspace,
        )

        return self._write_file(path, content, overwrite)

    def read_workspace_file(self, project: dict[str, Any], relative_path: str, workspace: str = "staging",) -> str:
        """
        Read a file inside selected workspace.
        """
        path = workspace_service.resolve_workspace_path(
            project=project,
            relative_path=relative_path,
            workspace=workspace,
        )

        if not path.exists():
            raise FileNotFoundError(f"Workspace file not found: {relative_path}")

        return read_text_file(path)

    def append_workspace_file(
        self,
        project: dict[str, Any],
        relative_path: str,
        content: str,
        workspace: str = "staging",
    ) -> str:
        """
        Append content to a workspace file.

        If the file does not exist, it will be created.
        """
        workspace_service.prepare_staging_workspace(project)

        path = workspace_service.resolve_workspace_path(
            project=project,
            relative_path=relative_path,
            workspace=workspace,
        )

        ensure_directory(path.parent)

        existing_content = ""
        if path.exists():
            existing_content = read_text_file(path)

        new_content = existing_content + content

        return write_text_file(path, new_content)

    def create_workspace_directory(
        self,
        project: dict[str, Any],
        relative_path: str,
        workspace: str = "staging",
    ) -> str:
        """
        Create a directory inside selected workspace.

        Example:
            frontend/src/components/auth
        """
        workspace_service.prepare_staging_workspace(project)

        path = workspace_service.resolve_workspace_path(
            project=project,
            relative_path=relative_path,
            workspace=workspace,
        )

        ensure_directory(path)

        return str(path)

    def workspace_file_exists(
        self,
        project: dict[str, Any],
        relative_path: str,
        workspace: str = "staging",
    ) -> bool:
        """
        Check whether a workspace file exists.
        """
        path = workspace_service.resolve_workspace_path(
            project=project,
            relative_path=relative_path,
            workspace=workspace,
        )

        return path.exists() and path.is_file()

    # ------------------------------------------------------------------
    # Frontend-specific operations
    # ------------------------------------------------------------------

    def write_frontend_file(
        self,
        project: dict[str, Any],
        relative_frontend_path: str,
        content: str,
        workspace: str = "staging",
        overwrite: bool = True,
    ) -> str:
        """
        Write a file inside frontend/.

        Example:
            relative_frontend_path = "src/pages/Login.jsx"

        This writes:
            workspaces/{project_slug}/staging/frontend/src/pages/Login.jsx
        """
        workspace_service.prepare_staging_workspace(project)

        path = workspace_service.resolve_frontend_path(
            project=project,
            relative_frontend_path=relative_frontend_path,
            workspace=workspace,
        )

        return self._write_file(path, content, overwrite)

    def read_frontend_file(
        self,
        project: dict[str, Any],
        relative_frontend_path: str,
        workspace: str = "staging",
    ) -> str:
        """
        Read a file inside frontend/.
        """
        path = workspace_service.resolve_frontend_path(
            project=project,
            relative_frontend_path=relative_frontend_path,
            workspace=workspace,
        )

        if not path.exists():
            raise FileNotFoundError(f"Frontend file not found: {relative_frontend_path}")

        return read_text_file(path)

    def create_frontend_directory(
        self,
        project: dict[str, Any],
        relative_frontend_path: str,
        workspace: str = "staging",
    ) -> str:
        """
        Create a directory inside frontend/.

        Example:
            src/components/auth
        """
        workspace_service.prepare_staging_workspace(project)

        path = workspace_service.resolve_frontend_path(
            project=project,
            relative_frontend_path=relative_frontend_path,
            workspace=workspace,
        )

        ensure_directory(path)

        return str(path)

    # ------------------------------------------------------------------
    # Backend-specific operations
    # ------------------------------------------------------------------

    def write_backend_file(
        self,
        project: dict[str, Any],
        relative_backend_path: str,
        content: str,
        workspace: str = "staging",
        overwrite: bool = True,
    ) -> str:
        """
        Write a file inside backend/.

        Example:
            relative_backend_path = "src/modules/auth/auth.routes.js"

        This writes:
            workspaces/{project_slug}/staging/backend/src/modules/auth/auth.routes.js
        """
        workspace_service.prepare_staging_workspace(project)

        path = workspace_service.resolve_backend_path(
            project=project,
            relative_backend_path=relative_backend_path,
            workspace=workspace,
        )

        return self._write_file(path, content, overwrite)

    def read_backend_file(
        self,
        project: dict[str, Any],
        relative_backend_path: str,
        workspace: str = "staging",
    ) -> str:
        """
        Read a file inside backend/.
        """
        path = workspace_service.resolve_backend_path(
            project=project,
            relative_backend_path=relative_backend_path,
            workspace=workspace,
        )

        if not path.exists():
            raise FileNotFoundError(f"Backend file not found: {relative_backend_path}")

        return read_text_file(path)

    def create_backend_directory(
        self,
        project: dict[str, Any],
        relative_backend_path: str,
        workspace: str = "staging",
    ) -> str:
        """
        Create a directory inside backend/.

        Example:
            src/modules/auth
        """
        workspace_service.prepare_staging_workspace(project)

        path = workspace_service.resolve_backend_path(
            project=project,
            relative_backend_path=relative_backend_path,
            workspace=workspace,
        )

        ensure_directory(path)

        return str(path)

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _write_file(
        self,
        path: Path,
        content: str,
        overwrite: bool,
    ) -> str:
        """
        Internal safe file write helper.

        overwrite=False is useful when an agent should not replace an existing file.
        """
        ensure_directory(path.parent)

        if path.exists() and not overwrite:
            raise FileExistsError(f"File already exists and overwrite=False: {path}")

        return write_text_file(path, content)


code_file_service = CodeFileService()