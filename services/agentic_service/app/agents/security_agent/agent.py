"""
Security Agent.

Coordinates all security validation components.
"""

from __future__ import annotations

from pathlib import Path

from app.agents.security_agent.gates.security_gate import SecurityGate
from app.agents.security_agent.llm.reviewer import LLMReviewer
from app.agents.security_agent.markdown_builder import SecurityMarkdownBuilder
from app.agents.security_agent.scanners.ast_scanner import ASTScanner
from app.agents.security_agent.scanners.dependency_scanner import DependencyScanner
from app.agents.security_agent.scanners.secret_scanner import SecretScanner
from app.agents.security_agent.schemas import (
    SecurityAgentInput,
    SecurityAgentOutput,
)


class SecurityAgent:
    """
    Main Security Agent.
    """

    def __init__(self, llm_provider=None):

        self.ast_scanner = ASTScanner()
        self.secret_scanner = SecretScanner()
        self.dependency_scanner = DependencyScanner()

        self.security_gate = SecurityGate()

        self.llm_reviewer = (
            LLMReviewer(llm_provider)
            if llm_provider
            else None
        )

    async def run(
        self,
        agent_input: SecurityAgentInput,
        project_path: Path,
    ) -> SecurityAgentOutput:
        """
        Execute the Security Agent.
        """

        findings = []

        python_files = self._collect_python_files(project_path)

        findings.extend(
            self._run_ast_scanner(python_files)
        )

        findings.extend(
            self._run_secret_scanner(python_files)
        )

        findings.extend(
            self.dependency_scanner.scan(project_path)
        )

        if self.llm_reviewer:

            findings.extend(
                await self._run_llm_review(python_files)
            )

        gate = self.security_gate.evaluate(findings)

        markdown = SecurityMarkdownBuilder.build(
            project_name=agent_input.project.get(
                "project_name",
                "Unknown Project",
            ),
            feature_name=agent_input.feature.get(
                "feature_name",
                "Unknown Feature",
            ),
            findings=findings,
            security_gate=gate,
        )

        return SecurityAgentOutput(
            security_report_json={
                "findings": findings
            },
            security_summary_json=gate["summary"],
            security_gate_json=gate,
            fix_recommendations_json={
                "recommendations": [
                    finding["recommendation"]
                    for finding in findings
                ]
            },
            security_report_markdown=markdown,
            artifact_ids=[],
        )

    def _collect_python_files(
        self,
        project_path: Path,
    ) -> list[Path]:
        """
        Collect Python files.
        """

        return list(
            project_path.rglob("*.py")
        )

    def _run_ast_scanner(
        self,
        files: list[Path],
    ) -> list[dict]:

        findings = []

        for file in files:
            findings.extend(
                self.ast_scanner.scan(file)
            )

        return findings

    def _run_secret_scanner(
        self,
        files: list[Path],
    ) -> list[dict]:

        findings = []

        for file in files:
            findings.extend(
                self.secret_scanner.scan(file)
            )

        return findings

    async def _run_llm_review(
        self,
        files: list[Path],
    ) -> list[dict]:

        findings = []

        for file in files:

            findings.extend(
                await self.llm_reviewer.review(file)
            )

        return findings