"""
Project Memory Service.

This service creates and maintains persistent JSON memory files for AutoForge.

Important idea:
- The LLM model is NOT the memory.
- AutoForge backend is the memory.
- Every agent receives memory/context before it works.
- After each task, memory is updated.

This service works alongside MongoDB.
MongoDB stores main system records such as projects, features, artifacts, approvals.
This service stores agent-friendly memory JSON files that are easy to inspect,
debug, and inject into prompts.

Folder structure created by this service:

memory/
  {project_slug}/
    project_memory.json
    project_decisions.json
    model_invocation_log.json
    project_file_manifest.json

    features/
      {feature_slug}/
        feature_memory.json
        uiux_memory.json
        coder_memory.json
        task_ledger.json
        context_snapshots/
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.utils.file_manager import ensure_directory, write_json_file, read_json_file
from app.utils.slugify import slugify


class ProjectMemoryService:
    """
    Handles project-level, feature-level, and agent-level memory files.
    """

    def __init__(self) -> None:
        """
        MEMORY_DIR is optional.

        If you later add this to config.py:
            MEMORY_DIR: str = "memory"

        this service will use it.

        If it does not exist in config.py yet, it safely falls back to "memory".
        """
        self.memory_root = Path(getattr(settings, "MEMORY_DIR", "memory"))

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def get_project_slug(self, project_name: str) -> str:
        """
        Convert project name into folder-safe slug.
        Example:
            E-commerce Platform -> e-commerce-platform
        """
        return slugify(project_name)

    def get_feature_slug(self, feature_name: str) -> str:
        """
        Convert feature name into feature folder slug.
        Example:
            Login -> feature-login
        """
        return f"feature-{slugify(feature_name)}"

    def get_project_memory_dir(self, project_name: str) -> Path:
        """
        Return memory/{project_slug}
        """
        project_slug = self.get_project_slug(project_name)
        return self.memory_root / project_slug

    def get_feature_memory_dir(self, project_name: str, feature_name: str) -> Path:
        """
        Return memory/{project_slug}/features/{feature_slug}
        """
        return (
            self.get_project_memory_dir(project_name)
            / "features"
            / self.get_feature_slug(feature_name)
        )

    def get_context_snapshot_dir(self, project_name: str, feature_name: str) -> Path:
        """
        Return memory/{project_slug}/features/{feature_slug}/context_snapshots
        """
        return self.get_feature_memory_dir(project_name, feature_name) / "context_snapshots"

    # ------------------------------------------------------------------
    # Initialization methods
    # ------------------------------------------------------------------

    def initialize_project_memory(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Create base project memory files if they do not already exist.

        This should be called when:
        - a project is created
        - an agent starts and memory does not exist yet
        """
        project_dir = self.get_project_memory_dir(project["project_name"])
        ensure_directory(project_dir)
        ensure_directory(project_dir / "features")

        project_memory_path = project_dir / "project_memory.json"
        decisions_path = project_dir / "project_decisions.json"
        model_log_path = project_dir / "model_invocation_log.json"
        file_manifest_path = project_dir / "project_file_manifest.json"

        if not project_memory_path.exists():
            project_memory = {
                "project_id": project["project_id"],
                "project_name": project["project_name"],
                "project_type": project.get("project_type"),
                "target_stack": project.get("target_stack", "MERN"),
                "created_at": self._now(),
                "last_updated": self._now(),
                "completed_features": [],
                "active_feature": None,
                "global_rules": [
                    "Generated application must use MERN stack only.",
                    "Do not generate unrelated features.",
                    "Do not overwrite approved artifacts.",
                    "Use patch-based file changes.",
                    "Use shared staging workspace for UI/UX and Coder Agent.",
                    "Do not hardcode secrets.",
                    "Human approval is required before moving to the next stage."
                ],
                "important_decisions": []
            }
            write_json_file(project_memory_path, project_memory)

        if not decisions_path.exists():
            decisions = {
                "project_id": project["project_id"],
                "decisions": [
                    {
                        "decision_id": "DEC-001",
                        "title": "Use MERN stack only",
                        "decision": "The generated application must use MongoDB, Express.js, React, Node.js, and Tailwind CSS.",
                        "applies_to": "entire_project",
                        "source": "project_constraint",
                        "created_at": self._now()
                    }
                ]
            }
            write_json_file(decisions_path, decisions)

        if not model_log_path.exists():
            write_json_file(model_log_path, {
                "project_id": project["project_id"],
                "invocations": []
            })

        if not file_manifest_path.exists():
            write_json_file(file_manifest_path, {
                "project_id": project["project_id"],
                "workspace": None,
                "files": []
            })

        return self.read_json(project_memory_path)

    def initialize_feature_memory(self, project: dict[str, Any], feature: dict[str, Any],) -> dict[str, Any]:
        """
        Create feature memory files if they do not exist.

        This memory tells agents:
        - which feature is active
        - which artifacts are approved
        - which stages are completed
        - what still needs to happen
        """
        feature_dir = self.get_feature_memory_dir(
            project_name=project["project_name"],
            feature_name=feature["feature_name"]
        )
        ensure_directory(feature_dir)
        ensure_directory(feature_dir / "context_snapshots")

        feature_memory_path = feature_dir / "feature_memory.json"

        if not feature_memory_path.exists():
            feature_memory = {
                "project_id": project["project_id"],
                "feature_id": feature["feature_id"],
                "feature_name": feature["feature_name"],
                "feature_description": feature.get("feature_description", ""),
                "feature_status": feature.get("feature_status", "created"),
                "current_agent": feature.get("current_agent"),
                "approved_artifacts": {},
                "completed_stages": [],
                "pending_stages": [
                    "requirement_agent",
                    "domain_agent",
                    "architecture_agent",
                    "uiux_agent",
                    "coder_agent"
                ],
                "last_updated": self._now()
            }
            write_json_file(feature_memory_path, feature_memory)

        # Create empty agent memory files for future use.
        self.initialize_agent_memory(project, feature, "requirement_agent")
        self.initialize_agent_memory(project, feature, "domain_agent")
        self.initialize_agent_memory(project, feature, "architecture_agent")
        self.initialize_agent_memory(project, feature, "uiux_agent")
        self.initialize_agent_memory(project, feature, "coder_agent")

        return self.read_json(feature_memory_path)

    def initialize_agent_memory(self, project: dict[str, Any], feature: dict[str, Any],agent_name: str,
    ) -> dict[str, Any]:
        """
        Create memory file for a specific agent.

        Example:
            uiux_agent -> uiux_memory.json  
            coder_agent -> coder_memory.json
        """
        feature_dir = self.get_feature_memory_dir(
            project_name=project["project_name"],
            feature_name=feature["feature_name"]
        )
        ensure_directory(feature_dir)

        short_name = agent_name.replace("_agent", "")
        memory_path = feature_dir / f"{short_name}_memory.json"

        if not memory_path.exists():
            memory = {
                "project_id": project["project_id"],
                "feature_id": feature["feature_id"],
                "agent_name": agent_name,
                "memory_version": 1,
                "last_updated": self._now(),
                "completed_tasks": [],
                "failed_tasks": [],
                "pending_tasks": [],
                "files_created": [],
                "files_modified": [],
                "patch_ids": [],
                "commands_requested": [],
                "validation_results": [],
                "important_decisions": [],
                "next_recommended_task": None
            }
            write_json_file(memory_path, memory)

        return self.read_json(memory_path)

    # ------------------------------------------------------------------
    # Read/write helpers
    # ------------------------------------------------------------------

    def read_project_memory(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Read project_memory.json.
        If missing, initialize it first.
        """
        self.initialize_project_memory(project)
        path = self.get_project_memory_dir(project["project_name"]) / "project_memory.json"
        return self.read_json(path)

    def read_feature_memory(self, project: dict[str, Any], feature: dict[str, Any],) -> dict[str, Any]:
        """
        Read feature_memory.json.
        If missing, initialize it first.
        """
        self.initialize_feature_memory(project, feature)
        path = (
            self.get_feature_memory_dir(project["project_name"], feature["feature_name"])
            / "feature_memory.json"
        )
        return self.read_json(path)

    def read_agent_memory(self, project: dict[str, Any], feature: dict[str, Any], agent_name: str,) -> dict[str, Any]:
        """
        Read memory for a specific agent.
        """
        self.initialize_agent_memory(project, feature, agent_name)
        short_name = agent_name.replace("_agent", "")
        path = (
            self.get_feature_memory_dir(project["project_name"], feature["feature_name"])
            / f"{short_name}_memory.json"
        )
        return self.read_json(path)

    def write_agent_memory(self, project: dict[str, Any], feature: dict[str, Any], agent_name: str, memory: dict[str, Any],) -> str:
        """
        Save updated agent memory.
        """
        short_name = agent_name.replace("_agent", "")
        path = (
            self.get_feature_memory_dir(project["project_name"], feature["feature_name"])
            / f"{short_name}_memory.json"
        )

        memory["last_updated"] = self._now()
        return write_json_file(path, memory)

    def save_context_snapshot(self, project: dict[str, Any],feature: dict[str, Any], agent_name: str, context_pack: dict[str, Any],) -> str:
        """
        Save a snapshot of the exact context given to an agent/model.

        This is very useful when models change because you can prove:
        - which model ran
        - what context it received
        - which task it executed
        """
        snapshot_dir = self.get_context_snapshot_dir(
            project_name=project["project_name"],
            feature_name=feature["feature_name"]
        )
        ensure_directory(snapshot_dir)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{agent_name}_context_{timestamp}.json"
        path = snapshot_dir / filename

        snapshot = {
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "agent_name": agent_name,
            "created_at": self._now(),
            "context_pack": context_pack
        }

        return write_json_file(path, snapshot)

    def read_json(self, path: str | Path) -> dict[str, Any]:
        """
        Read JSON file safely.
        """
        return read_json_file(path)

    def write_json(self, path: str | Path, data: dict[str, Any]) -> str:
        """
        Write JSON file safely.
        """
        return write_json_file(path, data)

    def _now(self) -> str:
        """
        Return UTC timestamp string.
        """
        return datetime.utcnow().isoformat() + "Z"


project_memory_service = ProjectMemoryService()