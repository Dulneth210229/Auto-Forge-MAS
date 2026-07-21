"""
LLM-based functional test generator for the QA Agent.
"""

import logging

from langchain_core.messages import HumanMessage

from app.agents.qa_agent.prompts import FUNCTIONAL_TEST_PROMPT
from app.providers.agentic_model_factory import get_agentic_chat_model

logger = logging.getLogger(__name__)


class LLMTestGenerator:
    """
    Uses the configured LLM to generate functional pytest test cases
    from application source code.
    """

    def __init__(self):
        self.chat_model = get_agentic_chat_model()

    async def generate_tests(self, source_code: str) -> str:
        """
        Generate pytest test cases from source code.

        Args:
            source_code: Source code to analyse.

        Returns:
            Executable pytest code.
        """

        logger.info("Generating functional tests using the LLM.")

        prompt = FUNCTIONAL_TEST_PROMPT.format(
            source_code=source_code
        )

        try:

            response = await self.chat_model.ainvoke(
                [HumanMessage(content=prompt)]
            )

            if hasattr(response, "content"):
                generated_code = response.content
            else:
                generated_code = str(response)

            generated_code = self._clean_response(generated_code)

            if not generated_code.strip():
                raise RuntimeError(
                    "LLM returned an empty response."
                )

            logger.info(
                "Successfully generated pytest test cases."
            )

            return generated_code

        except Exception as exc:

            logger.exception(
                "Failed to generate functional tests."
            )

            raise RuntimeError(
                f"LLM test generation failed: {exc}"
            ) from exc

    @staticmethod
    def _clean_response(response: str) -> str:
        """
        Remove markdown formatting returned by the LLM.

        Args:
            response: Raw LLM response.

        Returns:
            Clean executable Python code.
        """

        response = response.strip()

        response = response.replace(
            "```python",
            ""
        )

        response = response.replace(
            "```",
            ""
        )

        return response.strip()