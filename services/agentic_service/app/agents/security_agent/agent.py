"""
Security Agent.

Purpose:
- Perform deterministic security validation on generated source code.
- Execute static security scanners.
- Perform optional LLM-assisted secure code review.
- Generate security reports.
- Save artifacts for human review.

This agent follows the same architecture as the Requirement Agent.
"""

from pathlib import Path

from app.agents.security_agent.gates.security_gate import SecurityGate
from app.agents.security_agent.llm.reviewer import LLMReviewer
from app.agents.security_agent.markdown_builder import SecurityMarkdownBuilder
from app.agents.security_agent.scanners.ast_scanner import ASTScanner
from app.agents.security_agent.scanners.dependency_scanner import DependencyScanner
from app.agents.security_agent.scanners.secret_scanner import SecretScanner
from app.agents.security_agent.schemas import SecurityAgentOutput
from app.core.enums import AgentName, ArtifactFormat, ArtifactType, FeatureStatus
from app.schemas.agent_schema import AgentRunResponse
from app.schemas.security_schema import SecurityAgentRunRequest
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.workspace_service import workspace_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityAgent:
    """
    Main Security Agent.

    Responsibilities

    1. Load project and feature.
    2. Load generated workspace.
    3. Execute deterministic security scanners.
    4. Perform optional LLM review.
    5. Evaluate Security Gate.
    6. Generate security artifacts.
    """

    def __init__(self):
        """
        Initialize Security Agent dependencies.
        """

        self.ast_scanner = ASTScanner()
        self.secret_scanner = SecretScanner()
        self.dependency_scanner = DependencyScanner()

        self.security_gate = SecurityGate()

        self.workspace_service = workspace_service
        self.artifact_service = artifact_service

    async def run(
        self,
        feature_id: str,
        request: SecurityAgentRunRequest | None = None,
    ) -> AgentRunResponse:
        """
        Run the Security Agent.
        """

        logger.info(
            "Security Agent started for feature_id=%s",
            feature_id,
        )

        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])

        if not project:
            raise ValueError(
                "Project not found for this feature."
            )

        if request is None:
            request = SecurityAgentRunRequest()

        feature["feature_status"] = FeatureStatus.IN_PROGRESS
        feature["current_agent"] = AgentName.SECURITY

        repo = self.workspace_service.ensure_project_repo(
            project["project_id"]
        )

        workspace_path = Path(repo.working_tree_dir)

        logger.info(
            "Workspace loaded: %s",
            workspace_path,
        )

        # ---------------------------------
        # LLM Reviewer Initialization (Updated)
        # ---------------------------------
        llm_reviewer = None

        if request.enable_llm_review:
            try:
                llm_reviewer = LLMReviewer()
            except Exception as exc:
                logger.warning(
                    "Unable to initialize LLM Reviewer: %s",
                    exc,
                )

        findings = await self._run_security_analysis(
            workspace_path=workspace_path,
            llm_reviewer=llm_reviewer,
        )

        logger.info(
            "Security analysis completed. findings=%d",
            len(findings),
        )

        # Security Gate
        security_gate = self.security_gate.evaluate(
            findings
        )

        logger.info(
            "Security Gate: %s",
            security_gate["status"],
        )

        markdown_report = SecurityMarkdownBuilder.build(
            project_name=project["project_name"],
            feature_name=feature["feature_name"],
            findings=findings,
            security_gate=security_gate,
        )

        security_report = {
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "summary": security_gate["summary"],
            "status": security_gate["status"],
            "findings": findings,
        }

        output = SecurityAgentOutput(
            security_report_json=security_report,
            security_gate_json=security_gate,
            security_report_markdown=markdown_report,
        )

        version = self.artifact_service.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=AgentName.SECURITY,
            artifact_type=ArtifactType.SECURITY_REPORT,
        )

        artifact_ids = self._save_security_artifacts(
            project=project,
            feature=feature,
            output=output,
            version=version,
        )

        output.artifact_ids = artifact_ids

        feature["feature_status"] = FeatureStatus.COMPLETED
        feature["current_agent"] = None

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.SECURITY,
            status="completed",
            message=(
                f"Security analysis completed. "
                f"Security Gate: {security_gate['status']}. "
                f"{len(findings)} findings detected."
            ),
            artifact_ids=artifact_ids,
        )

    async def _run_security_analysis(
        self,
        workspace_path: Path,
        llm_reviewer: LLMReviewer | None,
    ) -> list[dict]:
        """
        Execute all security scanners.

        Steps:
        1. Collect source files.
        2. Run AST scanner.
        3. Run Secret scanner.
        4. Run Dependency scanner.
        5. Run optional LLM review.
        """

        findings: list[dict] = []

        source_files = self._collect_source_files(workspace_path)

        logger.info(
            "Collected %d source files.",
            len(source_files),
        )

        # ---------------------------------
        # AST Scanner
        # ---------------------------------
        for file_path in source_files:
            if file_path.suffix.lower() == ".py":
                findings.extend(
                    self.ast_scanner.scan(file_path)
                )

        # ---------------------------------
        # Secret Scanner
        # ---------------------------------
        for file_path in source_files:
            findings.extend(
                self.secret_scanner.scan(file_path)
            )

        # ---------------------------------
        # Dependency Scanner
        # ---------------------------------
        findings.extend(
            self.dependency_scanner.scan(
                workspace_path
            )
        )

        # ---------------------------------
        # LLM Review
        # ---------------------------------
        if llm_reviewer is not None:
            findings.extend(
                await self._run_llm_review(
                    llm_reviewer,
                    source_files,
                )
            )

        logger.info(
            "Security analysis produced %d findings.",
            len(findings),
        )

        return findings

    def _save_security_artifacts(
        self,
        project: dict,
        feature: dict,
        output: SecurityAgentOutput,
        version: int,
    ) -> list[str]:
        """
        Save Security Agent artifacts.
        """

        artifact_ids: list[str] = []

        markdown_artifact = self.artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.SECURITY,
            artifact_type=ArtifactType.SECURITY_REPORT,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename=self._build_security_report_filename(
                feature,
                "md",
                version_placeholder=True,
            ),
            content=output.security_report_markdown,
            version_override=version,
        )

        artifact_ids.append(markdown_artifact.artifact_id)

        json_artifact = self.artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.SECURITY,
            artifact_type=ArtifactType.SECURITY_REPORT,
            filename=self._build_security_report_filename(
                feature,
                "json",
                version_placeholder=True,
            ),
            data=output.security_report_json,
            version_override=version,
        )

        artifact_ids.append(json_artifact.artifact_id)

        logger.info(
            "Security artifacts saved. count=%d",
            len(artifact_ids),
        )

        return artifact_ids

    def _build_security_report_filename(
        self,
        feature: dict,
        extension: str,
        version_placeholder: bool = True,
        version: int | None = None,
    ) -> str:
        import re

        feature_name = feature.get("feature_name", "feature")

        feature_slug = feature_name.lower().strip()
        feature_slug = re.sub(r"[^a-z0-9]+", "_", feature_slug)
        feature_slug = feature_slug.strip("_")

        if not feature_slug:
            feature_slug = "feature"

        if version_placeholder:
            return f"{feature_slug}_security_report_v{{version}}.{extension}"

        if version is None:
            raise ValueError("version is required when version_placeholder=False")

        return f"{feature_slug}_security_report_v{version}.{extension}"

    def _collect_source_files(
        self,
        workspace_path: Path,
    ) -> list[Path]:

        supported_extensions = {".py", ".js", ".jsx", ".ts", ".tsx"}

        ignored_directories = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
        }

        source_files: list[Path] = []

        for file_path in workspace_path.rglob("*"):
            if not file_path.is_file():
                continue

            if any(
                ignored in file_path.parts
                for ignored in ignored_directories
            ):
                continue

            if file_path.suffix.lower() in supported_extensions:
                source_files.append(file_path)

        source_files.sort()

        return source_files

    async def _run_llm_review(
        self,
        llm_reviewer: LLMReviewer,
        source_files: list[Path],
    ) -> list[dict]:

        findings: list[dict] = []

        for file_path in source_files:
            logger.debug("LLM reviewing %s", file_path)

            findings.extend(
                await llm_reviewer.review(file_path)
            )

        return findings


security_agent = SecurityAgent()