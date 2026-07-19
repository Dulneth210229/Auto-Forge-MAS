"""
LLM Reviewer.

Performs LLM-assisted secure code review using the shared
Agentic Chat Model (LangChain).
"""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.messages import HumanMessage

from app.agents.security_agent.prompt import SecurityPromptBuilder
from app.providers.agentic_model_factory import get_agentic_chat_model


class LLMReviewer:
    """
    Performs LLM-assisted security review.

    Uses the shared Agentic Chat Model so the Security Agent
    follows the same LLM architecture as the Coder Agent.
    """

    def __init__(self):
        self.chat_model = get_agentic_chat_model()

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
            response = await self.chat_model.ainvoke(
                [
                    HumanMessage(content=prompt)
                ]
            )

            content = response.content

            # Some providers may return a list of content blocks.
            if isinstance(content, list):
                content = "".join(
                    block.get("text", "")
                    if isinstance(block, dict)
                    else str(block)
                    for block in content
                )

            data = json.loads(content)

            if isinstance(data, dict):
                return data.get("findings", [])

            return []

        except json.JSONDecodeError:
            return [
                {
                    "title": "Invalid LLM Response",
                    "description": "The LLM returned invalid JSON.",
                    "severity": "Low",
                    "line": 0,
                    "cwe": "N/A",
                    "recommendation": "Adjust the prompt so the model returns valid JSON.",
                }
            ]

        except Exception as ex:
            return [
                {
                    "title": "LLM Review Failed",
                    "description": str(ex),
                    "severity": "Low",
                    "line": 0,
                    "cwe": "N/A",
                    "recommendation": "Check the configured LLM provider or model.",
                }
            ]