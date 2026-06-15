"""
Architecture Agent implementation.

Purpose:
The Architecture Agent converts approved requirement artifacts into
architecture design artifacts.

Input:
- Approved SRS Markdown
- Approved Enhanced SRS Markdown
- Project type
- Feature name
- Target stack

Output:
- SDS Markdown
- SDS JSON
- Use Case Diagram PlantUML
- Architecture Traceability JSON

Important:
This version intentionally does NOT generate API contract or OpenAPI YAML.
"""

from app.agents.architecture_agent.parser import parse_architecture_agent_response
from app.agents.architecture_agent.prompt import ARCHITECTURE_AGENT_SYSTEM_PROMPT
from app.agents.architecture_agent.schemas import (
    ArchitectureAgentInput,
    ArchitectureAgentOutput,
)
from app.services.llm_provider_service import llm_provider_service


class ArchitectureAgent:
    """
    Architecture Agent class.

    This class is responsible only for architecture documentation.
    It should not know about FastAPI routes or artifact saving.

    Artifact saving happens in the API route/service layer.
    """

    async def run(
        self,
        agent_input: ArchitectureAgentInput
    ) -> ArchitectureAgentOutput:
        """
        Run Architecture Agent.

        Steps:
        1. Build prompt using approved SRS and Enhanced SRS.
        2. Call selected LLM provider.
        3. Parse and validate response.
        4. Return structured ArchitectureAgentOutput.
        """

        provider = llm_provider_service.get_provider()

        user_prompt = self._build_user_prompt(agent_input)

        raw_response = await provider.generate(
            prompt=user_prompt,
            system_prompt=ARCHITECTURE_AGENT_SYSTEM_PROMPT
        )

        return parse_architecture_agent_response(raw_response)

    def _build_user_prompt(
        self,
        agent_input: ArchitectureAgentInput
    ) -> str:
        """
        Build the user prompt sent to the LLM.

        The prompt includes:
        - project context
        - approved SRS
        - approved Enhanced SRS
        - human revision comment if available
        """

        revision_section = ""

        if agent_input.human_comment:
            revision_section = f"""
HUMAN REVISION COMMENT:
{agent_input.human_comment}
"""

        return f"""
PROJECT CONTEXT:
Project Type: {agent_input.project_type}
Feature Name: {agent_input.feature_name}
Target Stack: {agent_input.target_stack}

APPROVED SRS:
{agent_input.approved_srs_markdown}

APPROVED ENHANCED SRS:
{agent_input.approved_enhanced_srs_markdown}

{revision_section}

TASK:
Generate the Architecture Agent output for this feature.

Remember:
- Generate SDS Markdown.
- Generate SDS JSON.
- Generate PlantUML Use Case Diagram.
- Generate Architecture Traceability JSON.
- Do not generate API contract.
- Do not generate OpenAPI YAML.
- Do not generate UI.
- Do not generate source code.
- Return valid JSON only.
"""