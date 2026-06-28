"""
Coder Agent context builder.

Purpose:
    Load approved artifact content and build the minimal LLM context
    for the Coder Agent run. This module enforces the token-efficiency rule:
    never send more data to the LLM than the minimum required.

Architecture fit:
    - Called by agent.py before building the prompt.
    - Reads from artifact_service (approved artifact content from disk).
    - Reads from the in-memory store (project/feature metadata).
    - Does NOT call the LLM. Does NOT write any files.

Responsibilities:
    1. Load approved SRS, Enhanced SRS, SDS, UI Design content from disk.
    2. Summarize the previous project snapshot (paths + purposes only).
    3. Select only the files relevant to the new feature for the prompt.

Author: Coder Agent (Auto-Forge MAS)
Version: 1.0.0
"""

from typing import Any

from app.agents.coder_agent.schemas import GeneratedFile
from app.core.enums import AgentName, ArtifactType, ArtifactFormat
from app.services.artifact_service import artifact_service
from app.utils.logger import get_logger

logger = get_logger("coder_agent.context_builder")

# ---------------------------------------------------------------------------
# Keywords used to decide whether an existing file is "relevant"
# to the new feature being generated. These heuristics prevent sending
# the entire project to the LLM on every iteration.
# ---------------------------------------------------------------------------
_ALWAYS_RELEVANT_PATTERNS = [
    "index",
    "app",
    "server",
    "main",
    "config",
    "middleware",
    "router",
    "routes",
]


class ContextBuilder:
    """
    Builds the context the Coder Agent needs to generate code.

    This class encapsulates all artifact loading and context selection logic
    so that agent.py remains a clean orchestrator.
    """

    def load_approved_srs_content(self, feature_id: str) -> str:
        """
        Load the approved SRS Markdown content for this feature.

        Raises:
            ValueError: If no approved SRS artifact exists.
        """
        logger.info("[ContextBuilder] Loading approved SRS artifact for feature_id=%s", feature_id)

        artifact = artifact_service.get_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS,
            artifact_format=ArtifactFormat.MARKDOWN
        )

        if not artifact:
            raise ValueError(
                f"No approved SRS Markdown artifact found for feature_id={feature_id}. "
                "Approve the Requirement Agent output first."
            )

        content = artifact_service.read_artifact_content(artifact.artifact_id)
        logger.info("[ContextBuilder] Loaded SRS artifact_id=%s", artifact.artifact_id)
        return content

    def load_approved_enhanced_srs_content(self, feature_id: str) -> str:
        """
        Load the approved Enhanced SRS Markdown content for this feature.

        Raises:
            ValueError: If no approved Enhanced SRS artifact exists.
        """
        logger.info(
            "[ContextBuilder] Loading approved Enhanced SRS artifact for feature_id=%s",
            feature_id
        )

        artifact = artifact_service.get_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.DOMAIN,
            artifact_type=ArtifactType.ENHANCED_SRS,
            artifact_format=ArtifactFormat.MARKDOWN
        )

        if not artifact:
            raise ValueError(
                f"No approved Enhanced SRS Markdown artifact found for feature_id={feature_id}. "
                "Approve the Domain Agent output first."
            )

        content = artifact_service.read_artifact_content(artifact.artifact_id)
        logger.info("[ContextBuilder] Loaded Enhanced SRS artifact_id=%s", artifact.artifact_id)
        return content

    def load_approved_sds_content(self, feature_id: str) -> str:
        """
        Load the approved SDS Markdown content for this feature.

        Raises:
            ValueError: If no approved SDS artifact exists.
        """
        logger.info(
            "[ContextBuilder] Loading approved SDS artifact for feature_id=%s",
            feature_id
        )

        artifact = artifact_service.get_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.ARCHITECTURE,
            artifact_type=ArtifactType.SDS,
            artifact_format=ArtifactFormat.MARKDOWN
        )

        if not artifact:
            raise ValueError(
                f"No approved SDS Markdown artifact found for feature_id={feature_id}. "
                "Approve the Architecture Agent output first."
            )

        content = artifact_service.read_artifact_content(artifact.artifact_id)
        logger.info("[ContextBuilder] Loaded SDS artifact_id=%s", artifact.artifact_id)
        return content

    def load_approved_ui_design_content(self, feature_id: str) -> str | None:
        """
        Load the approved UI Design HTML content for this feature.

        Returns None if no approved UI artifact exists.
        This is intentionally non-blocking because the UI/UX Agent may not
        have run for this feature yet.
        """
        logger.info(
            "[ContextBuilder] Checking for approved UI Design artifact for feature_id=%s",
            feature_id
        )

        artifact = artifact_service.get_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.UIUX,
            artifact_type=ArtifactType.UI_DESIGN,
            artifact_format=ArtifactFormat.HTML
        )

        if not artifact:
            logger.info(
                "[ContextBuilder] No approved UI Design artifact found (non-blocking)."
            )
            return None

        content = artifact_service.read_artifact_content(artifact.artifact_id)
        logger.info("[ContextBuilder] Loaded UI Design artifact_id=%s", artifact.artifact_id)
        return content

    def load_previous_project_snapshot(
        self,
        project_id: str
    ) -> tuple[list[GeneratedFile], list[str]]:
        """
        Load the previous project snapshot from the latest approved CODE artifact.

        The snapshot contains all files from the last successful code generation.
        It is used by the project merger to classify new vs updated vs unchanged files.

        Returns:
            A tuple of:
                - List of GeneratedFile from the previous run (empty if first iteration).
                - List of feature names already implemented (empty if first iteration).

        Note:
            This method searches across ALL features in the project to find
            the latest approved CODE artifact. This is intentional: the Coder
            Agent must be aware of ALL previously generated files, not just
            files from the current feature.
        """
        logger.info(
            "[ContextBuilder] Loading previous project snapshot for project_id=%s",
            project_id
        )

        from app.services.in_memory_store import store
        from app.utils.json_utils import extract_json_object
        import json

        # Find all approved CODE artifacts across the project
        approved_code_artifacts = [
            artifact
            for artifact in store.artifacts.values()
            if (
                artifact["project_id"] == project_id
                and artifact["artifact_type"] == ArtifactType.CODE
                and artifact["approval_status"] == "approved"
                and artifact["agent_name"] == AgentName.CODER
            )
        ]

        if not approved_code_artifacts:
            logger.info(
                "[ContextBuilder] No previous approved CODE artifact found. "
                "This is the first feature iteration."
            )
            return [], []

        # Sort by version descending and take the most recent
        latest = max(approved_code_artifacts, key=lambda a: a["version"])

        logger.info(
            "[ContextBuilder] Found previous CODE artifact_id=%s version=%s",
            latest["artifact_id"],
            latest["version"]
        )

        try:
            raw_content = artifact_service.read_artifact_content(latest["artifact_id"])
            snapshot_data = extract_json_object(raw_content)
        except Exception as exc:
            logger.warning(
                "[ContextBuilder] Failed to parse previous CODE artifact: %s. "
                "Treating as first iteration.",
                exc
            )
            return [], []

        # Reconstruct GeneratedFile list from the snapshot JSON
        all_files: list[GeneratedFile] = []
        feature_names: list[str] = []

        raw_files = (
            snapshot_data.get("generated_files", [])
            + snapshot_data.get("updated_files", [])
            + snapshot_data.get("unchanged_files", [])
        )

        seen_paths: set[str] = set()
        for raw_file in raw_files:
            try:
                gf = GeneratedFile(**raw_file)
                if gf.file_path not in seen_paths:
                    all_files.append(gf)
                    seen_paths.add(gf.file_path)
            except Exception as exc:
                logger.warning(
                    "[ContextBuilder] Skipping malformed file entry in snapshot: %s", exc
                )

        # Extract feature names from artifact metadata
        metadata = snapshot_data.get("artifact_metadata", {})
        if isinstance(metadata, dict):
            feature_name = metadata.get("feature_name")
            if feature_name:
                feature_names.append(feature_name)

        # Also collect from integration notes or any previous_feature_names field
        previous_names = snapshot_data.get("previous_feature_names", [])
        if isinstance(previous_names, list):
            feature_names.extend(previous_names)

        feature_names = list(dict.fromkeys(feature_names))  # deduplicate, preserve order

        logger.info(
            "[ContextBuilder] Loaded %d existing files from previous snapshot. "
            "Known features: %s",
            len(all_files),
            feature_names
        )

        return all_files, feature_names

    def select_relevant_files(
        self,
        feature_name: str,
        all_files: list[GeneratedFile]
    ) -> list[GeneratedFile]:
        """
        Select only the files likely to be affected by the new feature.

        Strategy:
            1. Always include files matching _ALWAYS_RELEVANT_PATTERNS
               (index, app, server, main, config, middleware, router).
            2. Include files whose path contains a keyword from the feature name.
            3. Include route files and model files (always shared across features).

        This prevents sending the entire project to the LLM on iteration 3+.

        Args:
            feature_name: Name of the feature being developed.
            all_files:    All files from the previous project snapshot.

        Returns:
            A filtered subset of files most relevant to the new feature.
        """
        if not all_files:
            return []

        feature_keywords = [
            word.lower()
            for word in feature_name.replace("-", " ").replace("_", " ").split()
            if len(word) > 2
        ]

        relevant: list[GeneratedFile] = []

        for f in all_files:
            path_lower = f.file_path.lower()

            # Always include structural files
            if any(pattern in path_lower for pattern in _ALWAYS_RELEVANT_PATTERNS):
                relevant.append(f)
                continue

            # Include files matching the feature name keywords
            if any(keyword in path_lower for keyword in feature_keywords):
                relevant.append(f)
                continue

            # Include all route, model, and service files (shared infrastructure)
            if any(segment in path_lower for segment in ["route", "model", "service", "schema"]):
                relevant.append(f)
                continue

        logger.info(
            "[ContextBuilder] Selected %d / %d relevant files for feature '%s'.",
            len(relevant),
            len(all_files),
            feature_name
        )

        return relevant

    def get_project_metadata(self, feature_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Return the project and feature metadata dicts from the in-memory store.

        Args:
            feature_id: The feature being processed.

        Returns:
            A tuple of (project dict, feature dict).

        Raises:
            ValueError: If the feature or its parent project cannot be found.
        """
        from app.services.in_memory_store import store

        feature = store.features.get(feature_id)
        if not feature:
            raise ValueError(f"Feature not found in store: feature_id={feature_id}")

        project_id = feature.get("project_id")
        project = store.projects.get(project_id)
        if not project:
            raise ValueError(
                f"Project not found in store: project_id={project_id} "
                f"(referenced by feature_id={feature_id})"
            )

        return project, feature


# Module-level singleton — injected into agent.py
context_builder = ContextBuilder()
