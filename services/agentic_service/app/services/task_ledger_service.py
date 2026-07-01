"""
Task Ledger Service.

The task ledger tracks all implementation tasks for a feature.

Why this is needed:
- UI/UX Agent should execute only UI/UX tasks.
- Coder Agent should execute only Coder tasks.
- If the model changes, the next model can continue from the task ledger.
- We can track pending, completed, failed, blocked tasks.

The task ledger is stored here:

memory/{project_slug}/features/{feature_slug}/task_ledger.json
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.project_memory_service import project_memory_service
from app.utils.file_manager import write_json_file, read_json_file


class TaskLedgerService:
    """
    Manages feature-level task ledger.
    """

    DEFAULT_TASK_STATUSES = {
        "pending",
        "in_progress",
        "completed",
        "failed",
        "skipped",
        "blocked",
        "requires_human_review",
    }

    def get_task_ledger_path(self, project: dict[str, Any], feature: dict[str, Any],) -> Path:
        """
        Return the task ledger path for a feature.
        """
        feature_dir = project_memory_service.get_feature_memory_dir(
            project_name=project["project_name"],
            feature_name=feature["feature_name"]
        )
        return feature_dir / "task_ledger.json"

    def initialize_task_ledger(self, project: dict[str, Any], feature: dict[str, Any], tasks: list[dict[str, Any]] | None = None,) -> dict[str, Any]:
        """
        Create task_ledger.json if it does not exist.

        tasks can come from:
        - architecture implementation_plan_v1.json
        - architecture_plan_json
        - internal generated UI/UX execution plan
        """
        path = self.get_task_ledger_path(project, feature)

        if path.exists():
            return read_json_file(path)

        ledger_tasks = []

        for task in tasks or []:
            ledger_tasks.append({
                "task_id": task.get("task_id"),
                "title": task.get("title", ""),
                "owner_agent": task.get("owner_agent"),
                "task_type": task.get("task_type"),
                "priority": task.get("priority", 999),
                "status": "pending",
                "depends_on": task.get("depends_on", []),
                "started_at": None,
                "completed_at": None,
                "error_message": None,
                "retry_count": 0,
            })

        ledger = {
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "created_at": self._now(),
            "last_updated": self._now(),
            "tasks": ledger_tasks
        }

        write_json_file(path, ledger)
        return ledger

    def read_task_ledger(self, project: dict[str, Any], feature: dict[str, Any],) -> dict[str, Any]:
        """
        Read the task ledger.
        If missing, initialize an empty ledger.
        """
        path = self.get_task_ledger_path(project, feature)

        if not path.exists():
            return self.initialize_task_ledger(project, feature)

        return read_json_file(path)

    def write_task_ledger(self, project: dict[str, Any], feature: dict[str, Any], ledger: dict[str, Any],) -> str:
        """
        Save task ledger.
        """
        ledger["last_updated"] = self._now()
        path = self.get_task_ledger_path(project, feature)
        return write_json_file(path, ledger)

    def sync_tasks(self, project: dict[str, Any], feature: dict[str, Any], tasks: list[dict[str, Any]],) -> dict[str, Any]:
        """
        Add new tasks to the ledger without deleting existing task history.

        This is useful when:
        - Architecture Agent regenerates task plan
        - UI/UX Agent creates fallback UI tasks
        """
        ledger = self.read_task_ledger(project, feature)
        existing_ids = {task["task_id"] for task in ledger.get("tasks", [])}

        for task in tasks:
            task_id = task.get("task_id")

            if not task_id or task_id in existing_ids:
                continue

            ledger["tasks"].append({
                "task_id": task_id,
                "title": task.get("title", ""),
                "owner_agent": task.get("owner_agent"),
                "task_type": task.get("task_type"),
                "priority": task.get("priority", 999),
                "status": "pending",
                "depends_on": task.get("depends_on", []),
                "started_at": None,
                "completed_at": None,
                "error_message": None,
                "retry_count": 0,
            })

        self.write_task_ledger(project, feature, ledger)
        return ledger

    def get_pending_tasks_for_agent(self, project: dict[str, Any], feature: dict[str, Any], agent_name: str,) -> list[dict[str, Any]]:
        """
        Return pending tasks owned by a specific agent.

        Example:
            uiux_agent only receives owner_agent == "uiux_agent"
        """
        ledger = self.read_task_ledger(project, feature)

        tasks = [
            task
            for task in ledger.get("tasks", [])
            if task.get("owner_agent") == agent_name
            and task.get("status") == "pending"
        ]

        return sorted(tasks, key=lambda item: item.get("priority", 999))

    def mark_task_started(self,project: dict[str, Any], feature: dict[str, Any], task_id: str,) -> None:
        """
        Mark a task as in_progress.
        """
        self._update_task_status(
            project=project,
            feature=feature,
            task_id=task_id,
            status="in_progress",
            started_at=self._now()
        )

    def mark_task_completed(self, project: dict[str, Any], feature: dict[str, Any], task_id: str,) -> None:
        """
        Mark a task as completed.
        """
        self._update_task_status(
            project=project,
            feature=feature,
            task_id=task_id,
            status="completed",
            completed_at=self._now(),
            error_message=None
        )

    def mark_task_failed(self, project: dict[str, Any], feature: dict[str, Any], task_id: str, error_message: str,) -> None:
        """
        Mark a task as failed.
        """
        ledger = self.read_task_ledger(project, feature)

        for task in ledger.get("tasks", []):
            if task.get("task_id") == task_id:
                task["status"] = "failed"
                task["error_message"] = error_message
                task["retry_count"] = int(task.get("retry_count", 0)) + 1
                break

        self.write_task_ledger(project, feature, ledger)

    def _update_task_status(self, project: dict[str, Any], feature: dict[str, Any], task_id: str, status: str, **extra_fields: Any,) -> None:
        """
        Internal helper to update one task status.
        """
        if status not in self.DEFAULT_TASK_STATUSES:
            raise ValueError(f"Invalid task status: {status}")

        ledger = self.read_task_ledger(project, feature)

        for task in ledger.get("tasks", []):
            if task.get("task_id") == task_id:
                task["status"] = status

                for key, value in extra_fields.items():
                    task[key] = value

                break

        self.write_task_ledger(project, feature, ledger)

    def _now(self) -> str:
        """
        Return UTC timestamp string.
        """
        return datetime.utcnow().isoformat() + "Z"


task_ledger_service = TaskLedgerService()