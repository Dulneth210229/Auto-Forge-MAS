"""
Artifact service.

This service is responsible for:
- Creating artifact folders
- Writing artifact files
- Creating artifact metadata
- Finding artifacts by feature
- Versioning artifact files

Agents should not directly manage files.
They should call this service.

Important:
A single agent run may create multiple artifact files with the same version.

Example:
Requirement Agent creates:
- SRS_v1.md
- SRS_v1.json

Both files should be version 1.
That is why save_text_artifact() and save_json_artifact()
support version_override.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.enums import ApprovalStatus, AgentName, ArtifactType, ArtifactFormat
from app.schemas.artifact_schema import ArtifactResponse
from app.services.in_memory_store import store
from app.utils.file_manager import ensure_directory, write_text_file, write_json_file
from app.utils.id_generator import generate_id
from app.utils.slugify import slugify


class ArtifactService:
    """
    Handles all artifact-related operations.
    """

    STAGE_FOLDER_MAP = {
        AgentName.REQUIREMENT: "01_requirements",
        AgentName.DOMAIN: "02_domain",
        AgentName.ARCHITECTURE: "03_architecture",
        AgentName.UIUX: "04_uiux",
        AgentName.CODER: "05_code",
        AgentName.DEPLOYMENT: "06_deployment",
    }

    def create_feature_artifact_root(self,project_name: str,feature_name: str) -> Path:
        """
        Create the base artifact folders for a feature.

        Example:
            outputs/e-commerce-platform/feature-login/
        """
        project_slug = slugify(project_name)
        feature_slug = f"feature-{slugify(feature_name)}"

        root = Path(settings.OUTPUT_DIR) / project_slug / feature_slug

        for folder in self.STAGE_FOLDER_MAP.values():
            ensure_directory(root / folder)

        return root

    def get_stage_folder(self, project_name: str, feature_name: str, agent_name: AgentName ) -> Path:
        """
        Get the correct artifact folder for a specific agent.
        """
        root = self.create_feature_artifact_root(project_name, feature_name)
        return root / self.STAGE_FOLDER_MAP[agent_name]

    def get_next_version(self, feature_id: str, agent_name: AgentName, artifact_type: ArtifactType) -> int:
        """
        Find the next version number for a new artifact group.

        Example:
            If SRS_v1 already exists, next version will be 2.
        """
        existing_versions = [
            artifact["version"]
            for artifact in store.artifacts.values()
            if artifact["feature_id"] == feature_id
            and artifact["agent_name"] == agent_name
            and artifact["artifact_type"] == artifact_type
        ]

        if not existing_versions:
            return 1

        return max(existing_versions) + 1

    def save_text_artifact(self, project: dict[str, Any],
        feature: dict[str, Any],
        agent_name: AgentName,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat,
        filename: str,
        content: str,
        version_override: int | None = None
    ) -> ArtifactResponse:
        """
        Save a text-based artifact and register metadata.

        version_override lets multiple files share the same version.

        Example:
            SRS_v1.md and SRS_v1.json should both be version 1.
        """
        version = version_override or self.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=agent_name,
            artifact_type=artifact_type
        )

        stage_folder = self.get_stage_folder(
            project_name=project["project_name"],
            feature_name=feature["feature_name"],
            agent_name=agent_name
        )

        file_path = stage_folder / filename.replace("{version}", str(version))
        saved_path = write_text_file(file_path, content)

        return self._register_artifact(
            project_id=project["project_id"],
            feature_id=feature["feature_id"],
            agent_name=agent_name,
            artifact_type=artifact_type,
            artifact_format=artifact_format,
            file_path=saved_path,
            version=version
        )

    def save_json_artifact(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        agent_name: AgentName,
        artifact_type: ArtifactType,
        filename: str,
        data: dict[str, Any],
        version_override: int | None = None
    ) -> ArtifactResponse:
        """
        Save a JSON artifact and register metadata.

        version_override lets this JSON file share the same version
        as the related Markdown artifact.
        """
        version = version_override or self.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=agent_name,
            artifact_type=artifact_type
        )

        stage_folder = self.get_stage_folder(
            project_name=project["project_name"],
            feature_name=feature["feature_name"],
            agent_name=agent_name
        )

        file_path = stage_folder / filename.replace("{version}", str(version))
        saved_path = write_json_file(file_path, data)

        return self._register_artifact(
            project_id=project["project_id"],
            feature_id=feature["feature_id"],
            agent_name=agent_name,
            artifact_type=artifact_type,
            artifact_format=ArtifactFormat.JSON,
            file_path=saved_path,
            version=version
        )

    def _register_artifact(
        self,
        project_id: str,
        feature_id: str,
        agent_name: AgentName,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat,
        file_path: str,
        version: int
    ) -> ArtifactResponse:
        """
        Create artifact metadata and store it in the temporary in-memory store.
        """
        artifact_id = generate_id("artifact")
        created_at = datetime.utcnow()

        artifact = {
            "artifact_id": artifact_id,
            "project_id": project_id,
            "feature_id": feature_id,
            "agent_name": agent_name,
            "artifact_type": artifact_type,
            "artifact_format": artifact_format,
            "file_path": file_path,
            "version": version,
            "approval_status": ApprovalStatus.PENDING,
            "created_at": created_at,
        }

        store.artifacts[artifact_id] = artifact

        return ArtifactResponse(**artifact)

    def list_feature_artifacts(self, feature_id: str) -> list[ArtifactResponse]:
        """
        Return all artifacts generated for a feature.
        """
        return [
            ArtifactResponse(**artifact)
            for artifact in store.artifacts.values()
            if artifact["feature_id"] == feature_id
        ]

    def get_artifact(self, artifact_id: str) -> ArtifactResponse | None:
        """
        Return one artifact by ID.
        """
        artifact = store.artifacts.get(artifact_id)

        if not artifact:
            return None

        return ArtifactResponse(**artifact)


artifact_service = ArtifactService()