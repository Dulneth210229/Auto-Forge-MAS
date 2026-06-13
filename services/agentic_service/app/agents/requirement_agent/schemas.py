"""
Requirement Agent internal schemas.

These schemas are used inside the Requirement Agent itself.

The public API request schema is in:
    app/schemas/requirement_schema.py

This file focuses on the data passed internally inside the agent.
"""

from pydantic import BaseModel


class RequirementAgentInput(BaseModel):
    """
    Internal input passed to the Requirement Agent.

    project:
        Project metadata from store.projects.

    feature:
        Feature metadata from store.features.

    ba_input:
        Structured BA input from the API request.

    human_comment:
        Optional comment used when the user asks for revision.
    """

    project: dict
    feature: dict
    ba_input: dict
    human_comment: str | None = None


class RequirementAgentOutput(BaseModel):
    """
    Internal output produced by the Requirement Agent.

    srs_markdown:
        Human-readable SRS content.

    srs_json:
        Machine-readable SRS content.

    raw_llm_output:
        Original LLM response, useful for debugging if parsing fails.
    """

    srs_markdown: str
    srs_json: dict
    raw_llm_output: str