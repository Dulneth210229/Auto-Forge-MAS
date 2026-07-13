"""
LLM Reviewer.

Performs LLM-assisted secure code review.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.agents.security_agent.prompt import SecurityPromptBuilder


class LLMReviewer:
    """
    Performs LLM-assisted security review.

    The reviewer is independent from any specific provider.
    It works with the existing provider abstraction
    (Ollama, OpenAI, Anthropic, etc.).
    """

    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    async def review(self, file_path: Path) -> list[dict]:
        """
        Review a source code file.

        Args:
            file_path: Source code file.

        Returns:
            List of security findings.
        """

        try:
            source_code = file_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            return []

        prompt = SecurityPromptBuilder.build_security_review_prompt(
            file_path=str(file_path),
            source_code=source_code,
        )

        try:
            response = await self.llm_provider.generate(prompt)
        except Exception as ex:
            return [
                {
                    "title": "LLM Review Failed",
                    "description": str(ex),
                    "severity": "Low",
                    "line": 0,
                    "cwe": "N/A",
                    "recommendation": "Check the configured LLM provider.",
                }
            ]

        try:
            data = json.loads(response)

            if isinstance(data, dict):
                return data.get("findings", [])

            return []

        except Exception:

            return [
                {
                    "title": "Invalid LLM Response",
                    "description": "The LLM returned invalid JSON.",
                    "severity": "Low",
                    "line": 0,
                    "cwe": "N/A",
                    "recommendation": "Adjust the prompt or provider output format.",
                }
            ]