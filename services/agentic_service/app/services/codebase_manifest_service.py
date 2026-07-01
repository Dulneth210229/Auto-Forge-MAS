"""
Codebase Manifest Service.

This service tracks files inside the generated MERN project workspace.

Why this matters:
- UI/UX Agent and Coder Agent share the same workspace.
- We must know which files exist.
- We must know which agent created or modified each file.
- We must preserve previous approved features.
- We must avoid accidental overwrites.

Stored at:

memory/{project_slug}/project_file_manifest.json
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.project_memory_service import project_memory_service
from app.utils.file_manager import write_json_file, read_json_file


class CodebaseManifestService:
    """
    Tracks generated workspace files and their ownership.
    """

    def get_manifest_path(self, project: dict[str, Any]) -> Path:
        """
        Return project_file_manifest.json path.
        """
        project_dir = project_memory_service.get_project_memory_dir(project["project_name"])
        return project_dir / "project_file_manifest.json"

    def initialize_manifest(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure project_file_manifest.json exists.
        """
        project_memory_service.initialize_project_memory(project)

        path = self.get_manifest_path(project)

        if not path.exists():
            manifest = {
                "project_id": project["project_id"],
                "workspace": None,
                "files": [],
                "last_updated": self._now()
            }
            write_json_file(path, manifest)

        return read_json_file(path)

    def read_manifest(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Read file manifest.
        """
        return self.initialize_manifest(project)

    def set_workspace(self, project: dict[str, Any], workspace_path: str,) -> dict[str, Any]:
        """
        Save current workspace path used by the project.
        """
        manifest = self.initialize_manifest(project)
        manifest["workspace"] = workspace_path
        manifest["last_updated"] = self._now()

        write_json_file(self.get_manifest_path(project), manifest)
        return manifest

    def register_file(self, project: dict[str, Any], file_path: str, feature_id: str, created_by: str, purpose: str, last_modified_by: str | None = None,) -> dict[str, Any]:
        """
        Add or update a file record.

        file_path should be relative to the staging/current workspace.
        Example:
            frontend/src/pages/Login.jsx
        """
        manifest = self.initialize_manifest(project)

        existing = None
        for file_record in manifest.get("files", []):
            if file_record.get("path") == file_path:
                existing = file_record
                break

        if existing:
            existing["last_modified_by"] = last_modified_by or created_by
            existing["last_modified_at"] = self._now()
            existing["purpose"] = purpose
            existing["feature_id"] = feature_id
        else:
            manifest["files"].append({
                "path": file_path,
                "feature_id": feature_id,
                "created_by": created_by,
                "last_modified_by": last_modified_by or created_by,
                "purpose": purpose,
                "created_at": self._now(),
                "last_modified_at": self._now()
            })

        manifest["last_updated"] = self._now()
        write_json_file(self.get_manifest_path(project), manifest)

        return manifest

    def list_files_for_feature(self, project: dict[str, Any], feature_id: str,) -> list[dict[str, Any]]:
        """
        Return all files associated with a feature.
        """
        manifest = self.initialize_manifest(project)

        return [
            file_record
            for file_record in manifest.get("files", [])
            if file_record.get("feature_id") == feature_id
        ]

    def file_exists_in_manifest(self, project: dict[str, Any], file_path: str,) -> bool:
        """
        Check if a file is already known in the manifest.
        """
        manifest = self.initialize_manifest(project)

        return any(
            file_record.get("path") == file_path
            for file_record in manifest.get("files", [])
        )

    def _now(self) -> str:
        """
        Return UTC timestamp string.
        """
        return datetime.utcnow().isoformat() + "Z"


codebase_manifest_service = CodebaseManifestService()