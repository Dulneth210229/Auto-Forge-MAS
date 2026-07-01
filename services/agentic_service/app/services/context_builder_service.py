"""
Context Builder Service.

This service builds the context pack sent to an LLM.

Important principle:
Do not depend on chat history.
Do not send the full project every time.
Send only the focused context needed for the current task.

The context pack may include:
- project memory
- feature memory
- agent memory
- task ledger
- project decisions
- file manifest
- current task
- approved artifact summaries
- rules
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.project_memory_service import project_memory_service
from app.services.task_ledger_service import task_ledger_service
from app.services.codebase_manifest_service import codebase_manifest_service
from app.utils.file_manager import read_json_file, read_text_file


class ContextBuilderService:
    """
    Builds focused context packs for agents.
    """

    def build_agent_context(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        agent_name: str,
        current_task: dict[str, Any] | None = None,
        approved_artifacts: dict[str, str] | None = None,
        extra_rules: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Build a general context pack for any agent.

        Later we can add specialized methods:
            build_uiux_context()
            build_coder_context()
            build_architecture_context()
        """
        project_memory = project_memory_service.read_project_memory(project)
        feature_memory = project_memory_service.read_feature_memory(project, feature)
        agent_memory = project_memory_service.read_agent_memory(
            project=project,
            feature=feature,
            agent_name=agent_name
        )
        task_ledger = task_ledger_service.read_task_ledger(project, feature)
        file_manifest = codebase_manifest_service.read_manifest(project)

        project_decisions = self._read_project_decisions(project)

        artifact_summaries = {}
        for key, file_path in (approved_artifacts or {}).items():
            artifact_summaries[key] = self._safe_read_artifact_summary(file_path)

        context_pack = {
            "project": {
                "project_id": project["project_id"],
                "project_name": project["project_name"],
                "project_type": project.get("project_type"),
                "target_stack": project.get("target_stack", "MERN"),
            },
            "feature": {
                "feature_id": feature["feature_id"],
                "feature_name": feature["feature_name"],
                "feature_description": feature.get("feature_description", ""),
            },
            "project_memory": project_memory,
            "feature_memory": feature_memory,
            "agent_memory": agent_memory,
            "task_ledger": task_ledger,
            "project_decisions": project_decisions,
            "file_manifest": file_manifest,
            "current_task": current_task,
            "approved_artifact_summaries": artifact_summaries,
            "rules": self._base_rules(agent_name) + (extra_rules or []),
        }

        return context_pack

    def build_uiux_context(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        current_task: dict[str, Any],
        approved_artifacts: dict[str, str] | None = None,
        ui_preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build context specifically for UI/UX Agent.

        UI/UX Agent should not receive unnecessary backend implementation details.
        """
        context = self.build_agent_context(
            project=project,
            feature=feature,
            agent_name="uiux_agent",
            current_task=current_task,
            approved_artifacts=approved_artifacts,
            extra_rules=[
                "Execute only tasks assigned to uiux_agent.",
                "Use React + Tailwind CSS only.",
                "Do not create backend files.",
                "Do not modify database design.",
                "Do not modify API contract.",
                "Write frontend files only under frontend/.",
                "Return patch-ready structured JSON."
            ]
        )

        context["ui_preferences"] = ui_preferences or {}

        return context

    def build_coder_context(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        current_task: dict[str, Any],
        approved_artifacts: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Build context specifically for Coder Agent.

        Coder Agent can access the full project, but only modifies assigned files/tasks.
        """
        return self.build_agent_context(
            project=project,
            feature=feature,
            agent_name="coder_agent",
            current_task=current_task,
            approved_artifacts=approved_artifacts,
            extra_rules=[
                "Execute only tasks assigned to coder_agent.",
                "Generated app must use MERN stack only.",
                "Use patch-based changes.",
                "Do not overwrite previous approved features.",
                "Do not hardcode secrets.",
                "Maintain README.md and .gitignore."
            ]
        )

    def _read_project_decisions(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Read project_decisions.json.
        """
        project_memory_service.initialize_project_memory(project)
        project_dir = project_memory_service.get_project_memory_dir(project["project_name"])
        path = project_dir / "project_decisions.json"

        if not path.exists():
            return {"decisions": []}

        return read_json_file(path)

    def _safe_read_artifact_summary(self, file_path: str) -> dict[str, Any]:
        """
        Read artifact file safely and return a short summary.

        If JSON, return parsed JSON.
        If Markdown/text, return limited text.
        """
        path = Path(file_path)

        if not path.exists():
            return {
                "file_path": file_path,
                "status": "missing"
            }

        if path.suffix.lower() == ".json":
            return {
                "file_path": file_path,
                "type": "json",
                "content": read_json_file(path)
            }

        text = read_text_file(path)

        return {
            "file_path": file_path,
            "type": "text",
            "content_preview": text[:4000]
        }

    def _base_rules(self, agent_name: str) -> list[str]:
        """
        Rules common to every agent.
        """
        return [
            f"You are {agent_name} inside AutoForge.",
            "Stay within the approved feature scope.",
            "Do not invent unrelated features.",
            "Do not bypass human approval.",
            "Do not overwrite approved artifacts.",
            "Use existing memory and artifacts as source of truth.",
            "The LLM is not the memory; backend memory is the source of truth.",
        ]


context_builder_service = ContextBuilderService()