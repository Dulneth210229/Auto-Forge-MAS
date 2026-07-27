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

from pydantic import ValidationError

from app.core.config import settings
from app.core.enums import ApprovalStatus, AgentName, ArtifactType, ArtifactFormat
from app.schemas.artifact_schema import ArtifactResponse
from app.services.in_memory_store import store
from app.utils.file_manager import ensure_directory, write_text_file, write_json_file
from app.utils.id_generator import generate_id
from app.utils.logger import get_logger
from app.utils.slugify import slugify

logger = get_logger(__name__)


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
        AgentName.SECURITY: "06_security",
        AgentName.QA: "07_qa",
        AgentName.DEPLOYMENT: "08_deployment",
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

    def _hydrate_artifact_response(self, artifact: dict[str, Any]) -> ArtifactResponse:
        """
        Build an ArtifactResponse, computing size_bytes from the file on disk (never stored --
        the file is the source of truth, and this stays correct even if a file changes size for
        any reason). None if the file is missing rather than raising -- purely cosmetic, so a
        missing file should degrade gracefully, not break the whole list.
        """
        size_bytes = None
        try:
            size_bytes = Path(artifact["file_path"]).stat().st_size
        except OSError:
            pass

        return ArtifactResponse(**artifact, size_bytes=size_bytes)

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

        return self._hydrate_artifact_response(artifact)

    def list_feature_artifacts(self, feature_id: str) -> list[ArtifactResponse]:
        """
        Return all artifacts generated for a feature.

        Skips (and logs a warning for) any individual record that fails to validate against
        ArtifactResponse -- e.g. a legacy artifact_type value no longer in the ArtifactType enum
        (confirmed real case: old qa_agent "test_cases" records predating QA Agent being
        simplified to a stub) -- rather than letting one such record break this list for every
        other, perfectly valid artifact belonging to the same feature.
        """
        results = []

        for artifact in store.artifacts.values():
            if artifact["feature_id"] != feature_id:
                continue

            try:
                results.append(self._hydrate_artifact_response(artifact))
            except ValidationError as error:
                logger.warning(
                    "Skipping unparseable artifact %s for feature_id=%s: %s",
                    artifact.get("artifact_id"), feature_id, error,
                )

        return results

    def list_project_artifacts(
        self,
        project_id: str,
        agent_name: AgentName | None = None,
        artifact_type: ArtifactType | None = None,
        artifact_format: ArtifactFormat | None = None,
        approval_status: ApprovalStatus | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return raw artifact records across EVERY feature of a project,
        optionally filtered -- the first project-scoped artifact query
        (every record already carries project_id; all other lookups are
        feature-scoped). Added for the Architecture Agent's project-aware
        generation: a new feature's plan is generated with visibility into
        the previous features' approved plans.

        Enum filters match both the enum and its .value string form, since
        records written by different code paths store either.
        """

        def _matches(value: Any, expected) -> bool:
            return expected is None or value in (expected, expected.value)

        return [
            artifact
            for artifact in store.artifacts.values()
            if artifact.get("project_id") == project_id
            and _matches(artifact.get("agent_name"), agent_name)
            and _matches(artifact.get("artifact_type"), artifact_type)
            and _matches(artifact.get("artifact_format"), artifact_format)
            and _matches(artifact.get("approval_status"), approval_status)
        ]

    def get_artifact(self, artifact_id: str) -> ArtifactResponse | None:
        """
        Return one artifact by ID.
        """
        artifact = store.artifacts.get(artifact_id)

        if not artifact:
            return None

        return self._hydrate_artifact_response(artifact)
    def save_binary_artifact(
        self,
        project: dict[str, Any],
        feature: dict[str, Any],
        agent_name: AgentName,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat,
        filename: str,
        binary_content: bytes
    ) -> ArtifactResponse:
        """
        Save a binary artifact.

        This is mainly used for PNG diagrams generated from PlantUML.

        Example:
            usecase_v1.png
        """
        version = self.get_next_version(
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
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_bytes(binary_content)

        return self._register_artifact(
            project_id=project["project_id"],
            feature_id=feature["feature_id"],
            agent_name=agent_name,
            artifact_type=artifact_type,
            artifact_format=artifact_format,
            file_path=str(file_path),
            version=version
        )

    def get_latest_approved_artifact(
        self,
        feature_id: str,
        agent_name: AgentName,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat | None = None
    ) -> ArtifactResponse | None:
        """
        Return the latest approved artifact for a feature and agent.

        This is important for approval gates.

        Example:
        Architecture Agent should only run if:
        - approved SRS exists
        - approved Enhanced SRS exists
        """
        matching_artifacts = []

        for artifact in store.artifacts.values():
            is_same_feature = artifact["feature_id"] == feature_id
            is_same_agent = artifact["agent_name"] == agent_name
            is_same_type = artifact["artifact_type"] == artifact_type
            is_approved = artifact["approval_status"] == ApprovalStatus.APPROVED

            if not all([
                is_same_feature,
                is_same_agent,
                is_same_type,
                is_approved
            ]):
                continue

            if artifact_format is not None:
                if artifact["artifact_format"] != artifact_format:
                    continue

            matching_artifacts.append(artifact)

        if not matching_artifacts:
            return None

        latest = max(matching_artifacts, key=lambda item: item["version"])
        return self._hydrate_artifact_response(latest)

    def read_artifact_content(self, artifact_id: str) -> str:
        """
        Read artifact file content as text.

        This is used by agents to load previous approved artifacts.

        For now, Architecture Agent reads:
        - approved SRS markdown
        - approved Enhanced SRS markdown
        """
        artifact = store.artifacts.get(artifact_id)

        if not artifact:
            raise ValueError(f"Artifact not found: {artifact_id}")

        file_path = artifact["file_path"]

        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    def read_artifact_binary(self, artifact_id: str) -> bytes:
        """
        Read artifact file content as raw bytes (PNG diagrams/screenshots).

        Sibling of read_artifact_content -- used by the artifact content-serving
        API route so the frontend can display images directly.
        """
        artifact = store.artifacts.get(artifact_id)

        if not artifact:
            raise ValueError(f"Artifact not found: {artifact_id}")

        with open(artifact["file_path"], "rb") as file:
            return file.read()

artifact_service = ArtifactService()