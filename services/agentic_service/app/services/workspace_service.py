"""
Workspace Service.

This service manages the real generated MERN application workspace.

Important idea:
- outputs/ stores artifacts, logs, approvals, manifests, and evidence.
- memory/ stores project and agent memory.
- workspaces/ stores the actual generated MERN application code.

Workspace structure:

workspaces/
  {project_slug}/
    current/
      backend/
      frontend/
      README.md
      .gitignore
      .env.example

    staging/
      backend/
      frontend/
      README.md
      .gitignore
      .env.example

Meaning:
- current/ is the last approved working version.
- staging/ is where the current feature is being developed.
- UI/UX Agent writes frontend files into staging/frontend.
- Coder Agent writes backend, integration, README, .gitignore, and .env.example into staging.

This prevents confusion when merging features such as:
Login -> Signup -> Product Listing.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.utils.file_manager import ensure_directory, write_text_file
from app.utils.slugify import slugify


class WorkspaceService:
    """
    Manages current and staging workspaces for generated MERN projects.
    """

    def __init__(self) -> None:
        """
        WORKSPACE_DIR can be configured in .env/config.py.

        If it is not configured yet, we safely use "workspaces".
        """
        self.workspace_root = Path(getattr(settings, "WORKSPACE_DIR", "workspaces"))

    # ------------------------------------------------------------------
    # Slug and path helpers
    # ------------------------------------------------------------------

    def get_project_slug(self, project_name: str) -> str:
        """
        Convert project name to folder-safe slug.

        Example:
            E-commerce Platform -> e-commerce-platform
        """
        return slugify(project_name)

    def get_project_workspace_root(self, project: dict[str, Any]) -> Path:
        """
        Return:

        workspaces/{project_slug}
        """
        project_slug = self.get_project_slug(project["project_name"])
        return self.workspace_root / project_slug

    def get_current_workspace_path(self, project: dict[str, Any]) -> Path:
        """
        Return:

        workspaces/{project_slug}/current
        """
        return self.get_project_workspace_root(project) / "current"

    def get_staging_workspace_path(self, project: dict[str, Any]) -> Path:
        """
        Return:

        workspaces/{project_slug}/staging
        """
        return self.get_project_workspace_root(project) / "staging"

    def get_frontend_path(self, project: dict[str, Any], workspace: str = "staging") -> Path:
        """
        Return frontend path for current or staging workspace.
        """
        base = self._get_workspace_path(project, workspace)
        return base / "frontend"

    def get_backend_path(self, project: dict[str, Any], workspace: str = "staging") -> Path:
        """
        Return backend path for current or staging workspace.
        """
        base = self._get_workspace_path(project, workspace)
        return base / "backend"

    def _get_workspace_path(self, project: dict[str, Any], workspace: str) -> Path:
        """
        Return selected workspace path.

        Allowed values:
        - current
        - staging
        """
        if workspace == "current":
            return self.get_current_workspace_path(project)

        if workspace == "staging":
            return self.get_staging_workspace_path(project)

        raise ValueError("workspace must be either 'current' or 'staging'")

    # ------------------------------------------------------------------
    # Workspace lifecycle
    # ------------------------------------------------------------------

    def initialize_project_workspace(self, project: dict[str, Any]) -> Path:
        """
        Create base workspace folder for a project.

        This does not create current/staging by itself.
        """
        root = self.get_project_workspace_root(project)
        ensure_directory(root)
        return root

    def prepare_staging_workspace(self,project: dict[str, Any], reset_staging: bool = False,) -> Path:
        """
        Prepare staging workspace for a feature.

        If current/ exists:
            copy current/ into staging/

        If current/ does not exist:
            create a new MERN base staging workspace.

        reset_staging:
            If True, delete existing staging/ and rebuild it.
            Use carefully because staging may contain current work.
        """
        self.initialize_project_workspace(project)

        current_path = self.get_current_workspace_path(project)
        staging_path = self.get_staging_workspace_path(project)

        if reset_staging and staging_path.exists():
            shutil.rmtree(staging_path)

        if staging_path.exists():
            # Existing staging is reused to avoid deleting unfinished agent work.
            self._ensure_base_structure(staging_path)
            return staging_path

        if current_path.exists():
            # Copy the last approved project version into staging.
            shutil.copytree(current_path, staging_path)
            self._ensure_base_structure(staging_path)
            return staging_path

        # First feature: create fresh staging workspace.
        ensure_directory(staging_path)
        self._create_base_mern_workspace(staging_path, project)

        return staging_path

    def promote_staging_to_current(self, project: dict[str, Any], create_backup: bool = True,) -> Path:
        """
        Promote staging workspace to current workspace.

        This should be called only after human approval.

        For now, we provide the method but we will not automatically call it
        from UI/UX Agent. Later, Coder Agent or approval flow can call it.
        """
        staging_path = self.get_staging_workspace_path(project)
        current_path = self.get_current_workspace_path(project)

        if not staging_path.exists():
            raise FileNotFoundError("Staging workspace does not exist.")

        if current_path.exists() and create_backup:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = self.get_project_workspace_root(project) / f"current_backup_{timestamp}"
            shutil.copytree(current_path, backup_path)

        if current_path.exists():
            shutil.rmtree(current_path)

        shutil.copytree(staging_path, current_path)

        return current_path

    # ------------------------------------------------------------------
    # Base MERN workspace creation
    # ------------------------------------------------------------------

    def _create_base_mern_workspace(self, staging_path: Path, project: dict[str, Any],) -> None:
        """
        Create a minimal MERN folder structure.

        We do not install packages here.
        We only create safe folders and starter documentation files.

        Package files can be created later by the Coder Agent.
        """
        self._ensure_base_structure(staging_path)

        readme_path = staging_path / "README.md"
        gitignore_path = staging_path / ".gitignore"
        env_example_path = staging_path / ".env.example"

        if not readme_path.exists():
            write_text_file(
                readme_path,
                self._default_readme(project)
            )

        if not gitignore_path.exists():
            write_text_file(
                gitignore_path,
                self._default_gitignore()
            )

        if not env_example_path.exists():
            write_text_file(
                env_example_path,
                self._default_env_example()
            )

    def _ensure_base_structure(self, workspace_path: Path) -> None:
        """
        Ensure required MERN folders exist.

        This does not overwrite files.
        """
        ensure_directory(workspace_path)
        ensure_directory(workspace_path / "backend")
        ensure_directory(workspace_path / "backend" / "src")
        ensure_directory(workspace_path / "backend" / "src" / "config")
        ensure_directory(workspace_path / "backend" / "src" / "models")
        ensure_directory(workspace_path / "backend" / "src" / "modules")
        ensure_directory(workspace_path / "backend" / "src" / "middleware")
        ensure_directory(workspace_path / "backend" / "src" / "utils")

        ensure_directory(workspace_path / "frontend")
        ensure_directory(workspace_path / "frontend" / "src")
        ensure_directory(workspace_path / "frontend" / "src" / "pages")
        ensure_directory(workspace_path / "frontend" / "src" / "components")
        ensure_directory(workspace_path / "frontend" / "src" / "api")
        ensure_directory(workspace_path / "frontend" / "src" / "hooks")
        ensure_directory(workspace_path / "frontend" / "src" / "utils")
        ensure_directory(workspace_path / "frontend" / "src" / "assets")

    # ------------------------------------------------------------------
    # Safe path handling
    # ------------------------------------------------------------------

    def resolve_workspace_path(self, project: dict[str, Any], relative_path: str, workspace: str = "staging",) -> Path:
        """
        Resolve a relative path safely inside selected workspace.

        This prevents path traversal attacks such as:
            ../../.env
            C:/Users/...
            /etc/passwd

        Example allowed path:
            frontend/src/pages/Login.jsx
        """
        base_path = self._get_workspace_path(project, workspace).resolve()

        if Path(relative_path).is_absolute():
            raise ValueError("Absolute paths are not allowed.")

        candidate_path = (base_path / relative_path).resolve()

        if not self._is_relative_to(candidate_path, base_path):
            raise ValueError(f"Unsafe path outside workspace: {relative_path}")

        return candidate_path

    def resolve_frontend_path(self, project: dict[str, Any],  relative_frontend_path: str, workspace: str = "staging",) -> Path:
        """
        Resolve path safely inside frontend folder.

        The input should be relative to frontend/.

        Example:
            src/pages/Login.jsx
        """
        frontend_base = self.get_frontend_path(project, workspace).resolve()

        if Path(relative_frontend_path).is_absolute():
            raise ValueError("Absolute paths are not allowed.")

        candidate_path = (frontend_base / relative_frontend_path).resolve()

        if not self._is_relative_to(candidate_path, frontend_base):
            raise ValueError(f"Unsafe frontend path: {relative_frontend_path}")

        return candidate_path

    def resolve_backend_path(self,project: dict[str, Any], relative_backend_path: str, workspace: str = "staging",) -> Path:
        """
        Resolve path safely inside backend folder.

        The input should be relative to backend/.

        Example:
            src/modules/auth/auth.routes.js
        """
        backend_base = self.get_backend_path(project, workspace).resolve()

        if Path(relative_backend_path).is_absolute():
            raise ValueError("Absolute paths are not allowed.")

        candidate_path = (backend_base / relative_backend_path).resolve()

        if not self._is_relative_to(candidate_path, backend_base):
            raise ValueError(f"Unsafe backend path: {relative_backend_path}")

        return candidate_path

    def _is_relative_to(self, child: Path, parent: Path) -> bool:
        """
        Python 3.8 compatible version of Path.is_relative_to().
        """
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # Workspace inspection
    # ------------------------------------------------------------------

    def list_workspace_tree(self, project: dict[str, Any], workspace: str = "staging", max_files: int = 300,) -> list[str]:
        """
        Return a simple file tree list for the selected workspace.

        This is useful for context building and debugging.
        """
        base_path = self._get_workspace_path(project, workspace)

        if not base_path.exists():
            return []

        files: list[str] = []

        for path in base_path.rglob("*"):
            if path.is_file():
                files.append(str(path.relative_to(base_path)).replace("\\", "/"))

            if len(files) >= max_files:
                break

        return sorted(files)

    # ------------------------------------------------------------------
    # Default file templates
    # ------------------------------------------------------------------

    def _default_readme(self, project: dict[str, Any]) -> str:
        """
        Default README for a newly created generated app workspace.
        """
        return f"""# {project.get("project_name", "Generated MERN Application")}

This project was generated by AutoForge.

## Stack

- MongoDB
- Express.js
- React
- Node.js
- Tailwind CSS

## Project Structure

```text
backend/
frontend/
README.md
.gitignore
.env.example"""