"""
Model Invocation Service.

This service records which model was used for which agent/task.

Why this is important:
If output becomes inconsistent, we can check:
- Which model was used
- Which provider was used
- Which task was executed
- Which context snapshot was passed
- Whether the call succeeded or failed

Stored at:

memory/{project_slug}/model_invocation_log.json
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.project_memory_service import project_memory_service
from app.utils.file_manager import write_json_file, read_json_file
from app.utils.id_generator import generate_id


class ModelInvocationService:
    """
    Logs model/provider usage for traceability.
    """

    def get_log_path(self, project: dict[str, Any]) -> Path:
        """
        Return model_invocation_log.json path.
        """
        project_dir = project_memory_service.get_project_memory_dir(project["project_name"])
        return project_dir / "model_invocation_log.json"

    def initialize_log(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure model invocation log exists.
        """
        project_memory_service.initialize_project_memory(project)

        path = self.get_log_path(project)

        if not path.exists():
            log = {
                "project_id": project["project_id"],
                "invocations": []
            }
            write_json_file(path, log)

        return read_json_file(path)

    def log_invocation(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        agent_name: str,
        task_id: str | None,
        provider: str,
        model: str,
        temperature: float | None = None,
        context_snapshot_path: str | None = None,
        status: str = "completed",
        error_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Add one model invocation record.
        """
        log = self.initialize_log(project)

        record = {
            "invocation_id": generate_id("llm"),
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "agent_name": agent_name,
            "task_id": task_id,
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "context_snapshot_path": context_snapshot_path,
            "status": status,
            "error_message": error_message,
            "created_at": self._now()
        }

        log["invocations"].append(record)
        write_json_file(self.get_log_path(project), log)

        return record

    def read_log(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Read model invocation log.
        """
        return self.initialize_log(project)

    def _now(self) -> str:
        """
        Return UTC timestamp string.
        """
        return datetime.utcnow().isoformat() + "Z"


model_invocation_service = ModelInvocationService()