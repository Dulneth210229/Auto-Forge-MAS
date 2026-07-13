"""
Security Agent.

Purpose:
- Perform security validation on generated source code.
- Execute deterministic security scanners.
- Perform optional LLM-assisted code review.
- Generate security artifacts.
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
from app.core.enums import AgentName, FeatureStatus
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
    """

    def __init__(self):
        """
        Initialize Security Agent dependencies.
        """

        # Security scanners
        self.ast_scanner = ASTScanner()
        self.secret_scanner = SecretScanner()
        self.dependency_scanner = DependencyScanner()

        # Security components
        self.security_gate = SecurityGate()
        self.markdown_builder = SecurityMarkdownBuilder()

        # Shared services
        self.workspace_service = workspace_service
        self.artifact_service = artifact_service

        # Created only when LLM review is enabled
        self.llm_reviewer = None

    async def run(
        self,
        feature_id: str,
        request: SecurityAgentRunRequest,
    ) -> AgentRunResponse:
        """
        Run the Security Agent.

        Steps (implemented gradually):

        1. Load feature
        2. Load project
        3. Load workspace
        4. Execute scanners
        5. Evaluate security gate
        6. Save artifacts
        """

        logger.info(
            "Security Agent started for feature_id=%s",
            feature_id,
        )

        # -----------------------------
        # Load Feature
        # -----------------------------
        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        # -----------------------------
        # Load Project
        # -----------------------------
        project = store.projects.get(feature["project_id"])

        if not project:
            raise ValueError(
                "Project not found for this feature."
            )

        # -----------------------------
        # Update Feature Status
        # -----------------------------
        feature["feature_status"] = FeatureStatus.IN_PROGRESS
        feature["current_agent"] = AgentName.SECURITY

        # -----------------------------
        # Load Workspace
        # -----------------------------
        repo = self.workspace_service.ensure_project_repo(
            project["project_id"]
        )

        workspace_path = Path(repo.working_tree_dir)

        logger.info(
            "Workspace loaded: %s",
            workspace_path,
        )

        # -------------------------------------------------
        # Scanner execution will be implemented next step.
        # -------------------------------------------------

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.SECURITY,
            status="running",
            message=(
                "Security Agent initialized successfully. "
                "Scanner execution will be implemented next."
            ),
            artifact_ids=[],
        )


security_agent = SecurityAgent()