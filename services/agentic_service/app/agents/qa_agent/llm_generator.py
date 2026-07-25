"""
LLM-based functional test generator for the QA Agent.
"""

from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage

from app.agents.qa_agent.prompts import FUNCTIONAL_TEST_PROMPT
from app.providers.agentic_model_factory import get_agentic_chat_model

logger = logging.getLogger(__name__)


class LLMTestGenerator:
    """
    Uses the configured LLM to generate functional tests
    for different source code languages.
    """

    def __init__(self):
        self.chat_model = get_agentic_chat_model()

    async def generate_tests(
        self,
        source_code: str,
        file_extension: str,
    ) -> str:
        """
        Generate functional test cases.

        Args:
            source_code: Source code to analyse.
            file_extension: Extension of the source file.

        Returns:
            Executable test code.
        """

        framework = self._get_test_framework(file_extension)

        logger.info(
            "Generating %s tests for %s files.",
            framework,
            file_extension,
        )

        prompt = FUNCTIONAL_TEST_PROMPT.format(
            framework=framework,
            language=file_extension,
            source_code=source_code,
        )

        try:

            response = await self.chat_model.ainvoke(
                [HumanMessage(content=prompt)]
            )

            generated_code = (
                response.content
                if hasattr(response, "content")
                else str(response)
            )

            generated_code = self._clean_response(
                generated_code
            )

            valid_prefixes = (
                "import",
                "const",
                "let",
                "var",
                "describe",
                "test",
                "it",
            )

            if not generated_code.lstrip().startswith(valid_prefixes):
                raise RuntimeError(
                    "LLM returned non-executable test code."
                )

            if not generated_code.strip():
                raise RuntimeError(
                    "LLM returned an empty response."
                )

            logger.info(
                "Successfully generated %s test cases.",
                framework,
            )

            return generated_code

        except Exception as exc:

            logger.exception(
                "Failed generating functional tests."
            )

            raise RuntimeError(
                f"LLM test generation failed: {exc}"
            ) from exc

    @staticmethod
    def _get_test_framework(
        file_extension: str,
    ) -> str:
        """
        Determine the appropriate testing framework.
        """

        extension = file_extension.lower()

        mapping = {
            ".py": "pytest",
            ".js": "Jest",
            ".jsx": "React Testing Library with Jest",
            ".ts": "Jest",
            ".tsx": "React Testing Library with Jest",
        }

        return mapping.get(
            extension,
            "pytest",
        )

    @staticmethod
    def _clean_response(response: str) -> str:
        """
        Remove markdown and explanatory text returned by the LLM.
        """

        response = response.strip()

        # Remove markdown fences
        response = re.sub(r"^```[a-zA-Z]*\n?", "", response)
        response = re.sub(r"\n?```$", "", response)

        # Remove everything before the first line of code
        start_match = re.search(
            r"^(import\s|const\s|let\s|var\s|describe\s*\(|test\s*\(|it\s*\()",
            response,
            flags=re.MULTILINE,
        )

        if start_match:
            response = response[start_match.start():]

        # Remove common explanatory text appended after the code
        end_patterns = [
            r"\nNote that.*",
            r"\nThe above.*",
            r"\nThese tests.*",
            r"\nThis test.*",
            r"\nExplanation:.*",
            r"\nIn summary.*",
        ]

        for pattern in end_patterns:
            response = re.sub(
                pattern,
                "",
                response,
                flags=re.DOTALL | re.IGNORECASE,
            )

        return response.strip()