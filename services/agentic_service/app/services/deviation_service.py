"""
Deviation Service.

This service records situations where an agent needs to deviate from the
approved architecture or implementation plan.

Why this matters:
Agents should not silently make major decisions.

Examples requiring deviation request:
- Install dependency not listed in dependency plan.
- Add UI element not approved in requirements.
- Change API contract.
- Change database schema.
- Modify previous approved feature behavior.
- Delete or rename files.
- Change generated application stack.

Deviation requests are stored in both:

memory/{project_slug}/features/{feature_slug}/deviation_requests/

and, if possible:

outputs/{project_slug}/{feature_slug}/{stage_folder}/deviation_requests/

For UI/UX Agent:
    stage_folder = 04_uiux

For Coder Agent:
    stage_folder = 05_code
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.project_memory_service import project_memory_service
from app.utils.file_manager import ensure_directory, write_json_file
from app.utils.id_generator import generate_id
from app.utils.slugify import slugify


class DeviationService:
    """
    Creates and stores deviation request artifacts.
    """

    STAGE_FOLDER_BY_AGENT = {
        "requirement_agent": "01_requirements",
        "domain_agent": "02_domain",
        "architecture_agent": "03_architecture",
        "uiux_agent": "04_uiux",
        "coder_agent": "05_code",
        "security_agent": "06_security",
        "qa_agent": "07_qa",
    }

    def __init__(self) -> None:
        """
        OUTPUT_DIR is expected to exist in settings.
        If not, fallback to "outputs".
        """
        self.output_root = Path(getattr(settings, "OUTPUT_DIR", "outputs"))

    def create_deviation_request(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        agent_name: str,
        task_id: str | None,
        reason: str,
        suggested_change: str,
        impact: str,
        requires_human_approval: bool = True,
        severity: str = "medium",
        status: str = "pending",
    ) -> dict[str, Any]:
        """
        Create one deviation request.

        The agent should call this instead of silently making risky changes.
        """
        deviation_id = generate_id("dev")

        deviation = {
            "deviation_id": deviation_id,
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "agent_name": agent_name,
            "task_id": task_id,
            "reason": reason,
            "suggested_change": suggested_change,
            "impact": impact,
            "severity": severity,
            "requires_human_approval": requires_human_approval,
            "status": status,
            "created_at": self._now(),
        }

        memory_path = self._save_to_memory(project, feature, deviation)
        output_path = self._save_to_outputs(project, feature, agent_name, deviation)

        deviation["memory_path"] = memory_path
        deviation["output_path"] = output_path

        # Save again after adding paths.
        write_json_file(memory_path, deviation)

        if output_path:
            write_json_file(output_path, deviation)

        return deviation

    def _save_to_memory(self, project: dict[str, Any], feature: dict[str, Any], deviation: dict[str, Any],) -> str:
        """
        Save deviation request to memory directory.
        """
        feature_dir = project_memory_service.get_feature_memory_dir(
            project_name=project["project_name"],
            feature_name=feature["feature_name"],
        )

        deviation_dir = feature_dir / "deviation_requests"
        ensure_directory(deviation_dir)

        path = deviation_dir / f"{deviation['deviation_id']}.json"

        write_json_file(path, deviation)

        return str(path)

    def _save_to_outputs(self, project: dict[str, Any], feature: dict[str, Any], agent_name: str, deviation: dict[str, Any],) -> str | None:
        """
        Save deviation request to outputs folder.

        This makes the deviation visible as an agent artifact/evidence.
        """
        stage_folder = self.STAGE_FOLDER_BY_AGENT.get(agent_name)

        if not stage_folder:
            return None

        project_slug = slugify(project["project_name"])
        feature_slug = f"feature-{slugify(feature['feature_name'])}"

        output_dir = (
            self.output_root
            / project_slug
            / feature_slug
            / stage_folder
            / "deviation_requests"
        )
        ensure_directory(output_dir)

        path = output_dir / f"{deviation['deviation_id']}.json"

        write_json_file(path, deviation)

        return str(path)

    def _now(self) -> str:
        """
        Return UTC timestamp string.
        """
        return datetime.utcnow().isoformat() + "Z"


deviation_service = DeviationService()