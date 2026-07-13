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

from app.agents.security_agent.gates.security_gate import SecurityGate
from app.agents.security_agent.llm.reviewer import LLMReviewer
from app.agents.security_agent.markdown_builder import SecurityMarkdownBuilder
from app.agents.security_agent.scanners.ast_scanner import ASTScanner
from app.agents.security_agent.scanners.dependency_scanner import DependencyScanner
from app.agents.security_agent.scanners.secret_scanner import SecretScanner
from app.services.artifact_service import artifact_service
from app.services.workspace_service import workspace_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityAgent:
    """
    Main Security Agent.

    Responsibilities:
    1. Load project and feature.
    2. Load generated workspace.
    3. Execute security scanners.
    4. Evaluate security findings.
    5. Generate security reports.
    6. Save security artifacts.
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

        # Workspace and artifacts
        self.workspace_service = workspace_service
        self.artifact_service = artifact_service

        # LLM reviewer
        self.llm_reviewer = None


security_agent = SecurityAgent()