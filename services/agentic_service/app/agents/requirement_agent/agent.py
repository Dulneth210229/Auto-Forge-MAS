"""
Requirement Agent implementation.

Purpose:
- Receive structured BA input.
- Generate Software Requirements Specification using the selected LLM provider.
- Parse the LLM output.
- Validate required fields.
- Save SRS Markdown and SRS JSON artifacts.
- Return artifact IDs to the API route.

This agent does NOT:
- generate source code
- generate UI
- generate SDS
- generate diagrams
- move to Domain Agent automatically

Human approval is still required after this agent completes.
"""

from app.agents.requirement_agent.prompt import (
    REQUIREMENT_AGENT_SYSTEM_PROMPT,
    build_requirement_user_prompt,
)
from app.agents.requirement_agent.schemas import (
    RequirementAgentInput,
    RequirementAgentOutput,
)
from app.core.enums import (
    AgentName,
    ArtifactFormat,
    ArtifactType,
    FeatureStatus,
)
from app.schemas.agent_schema import AgentRunResponse
from app.schemas.requirement_schema import RequirementAgentRunRequest
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.llm_provider_service import llm_provider_service
from app.utils.json_utils import extract_json_object, ensure_keys_exist
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequirementAgent:
    """
    Requirement Agent class.

    This class contains the full backend logic for generating the initial SRS.
    """

    REQUIRED_TOP_LEVEL_KEYS = [
        "srs_markdown",
        "srs_json",
    ]

    REQUIRED_SRS_JSON_KEYS = [
        "project_id",
        "project_name",
        "project_type",
        "feature_id",
        "feature_name",
        "target_stack",
        "architectural_style",
        "business_goal",
        "functional_requirements",
        "non_functional_requirements",
        "acceptance_criteria",
        "constraints",
        "assumptions",
        "traceability",
    ]

    async def run(
        self,
        feature_id: str,
        request: RequirementAgentRunRequest
    ) -> AgentRunResponse:
        """
        Main entry point for running the Requirement Agent.

        Steps:
        1. Load feature.
        2. Load project.
        3. Merge project/feature metadata with BA input.
        4. Call selected LLM provider.
        5. Parse and validate LLM output.
        6. Save SRS Markdown and SRS JSON artifacts.
        7. Return artifact IDs.
        """

        logger.info("Requirement Agent started for feature_id=%s", feature_id)

        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])

        if not project:
            raise ValueError("Project not found for this feature.")

        # Mark feature as in progress while this agent runs.
        feature["feature_status"] = FeatureStatus.IN_PROGRESS
        feature["current_agent"] = AgentName.REQUIREMENT

        # Convert Pydantic BA input model into a plain dictionary.
        # mode="json" converts enum values into strings.
        ba_input = request.ba_input.model_dump(mode="json")

        # Fill missing BA values from existing project/feature metadata.
        ba_input = self._complete_ba_input_from_project_and_feature(
            project=project,
            feature=feature,
            ba_input=ba_input
        )

        agent_input = RequirementAgentInput(
            project=project,
            feature=feature,
            ba_input=ba_input,
            human_comment=request.human_comment
        )

        agent_output = await self._generate_srs(agent_input)

        # Get a shared version number for both SRS files.
        version = artifact_service.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS
        )

        markdown_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename="SRS_v{version}.md",
            content=agent_output.srs_markdown,
            version_override=version
        )

        json_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS,
            filename="SRS_v{version}.json",
            data=agent_output.srs_json,
            version_override=version
        )

        logger.info(
            "Requirement Agent completed for feature_id=%s with artifacts=%s",
            feature_id,
            [markdown_artifact.artifact_id, json_artifact.artifact_id]
        )

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.REQUIREMENT,
            status="completed",
            message=(
                "Requirement Agent completed successfully. "
                "SRS Markdown and SRS JSON artifacts were generated. "
                "Human approval is required before Domain Agent can run."
            ),
            artifact_ids=[
                markdown_artifact.artifact_id,
                json_artifact.artifact_id,
            ]
        )

    async def _generate_srs(
        self,
        agent_input: RequirementAgentInput
    ) -> RequirementAgentOutput:
        """
        Generate the SRS by calling the selected LLM provider.

        The selected provider can be:
        - Ollama
        - OpenAI
        - Any future provider added through the provider abstraction
        """

        provider = llm_provider_service.get_provider()

        user_prompt = build_requirement_user_prompt(
            project=agent_input.project,
            feature=agent_input.feature,
            ba_input=agent_input.ba_input,
            human_comment=agent_input.human_comment
        )

        raw_output = await provider.invoke_agent([
            {
                "role": "system",
                "content": REQUIREMENT_AGENT_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ])

        parsed_output = self._parse_and_validate_llm_output(raw_output)

        return RequirementAgentOutput(
            srs_markdown=parsed_output["srs_markdown"],
            srs_json=parsed_output["srs_json"],
            raw_llm_output=raw_output
        )

    def _parse_and_validate_llm_output(self, raw_output: str) -> dict:
        """
        Parse and validate LLM output.

        Expected structure:
        {
            "srs_markdown": "...",
            "srs_json": {...}
        }

        If the LLM returns invalid JSON, this method raises a clear error.
        """

        parsed = extract_json_object(raw_output)

        ensure_keys_exist(parsed, self.REQUIRED_TOP_LEVEL_KEYS)

        srs_markdown = parsed.get("srs_markdown")
        srs_json = parsed.get("srs_json")

        if not isinstance(srs_markdown, str) or not srs_markdown.strip():
            raise ValueError("srs_markdown must be a non-empty string.")

        if not isinstance(srs_json, dict):
            raise ValueError("srs_json must be a JSON object.")

        ensure_keys_exist(srs_json, self.REQUIRED_SRS_JSON_KEYS)

        self._validate_stable_ids(srs_json)

        return parsed

    def _validate_stable_ids(self, srs_json: dict) -> None:
        """
        Validate that key requirement sections contain stable IDs.

        This is important because later agents need traceability.
        Example:
            FR-001 -> AC-001 -> Code file
        """

        id_required_sections = [
            "functional_requirements",
            "non_functional_requirements",
            "acceptance_criteria",
        ]

        for section_name in id_required_sections:
            section = srs_json.get(section_name, [])

            if not isinstance(section, list):
                raise ValueError(f"{section_name} must be a list.")

            if not section:
                raise ValueError(f"{section_name} must not be empty.")

            for index, item in enumerate(section):
                if not isinstance(item, dict):
                    raise ValueError(
                        f"{section_name}[{index}] must be an object."
                    )

                if not item.get("id"):
                    raise ValueError(
                        f"{section_name}[{index}] is missing a stable ID."
                    )

                if not item.get("description"):
                    raise ValueError(
                        f"{section_name}[{index}] is missing description."
                    )

    def _complete_ba_input_from_project_and_feature(
        self,
        project: dict,
        feature: dict,
        ba_input: dict
    ) -> dict:
        """
        Fill missing BA input fields using project and feature metadata.

        Example:
        If the user does not send project_type in ba_input,
        we use project["project_type"].

        This keeps Swagger requests flexible.
        """

        completed = dict(ba_input)

        completed["project_name"] = project["project_name"]
        completed["project_id"] = project["project_id"]
        completed["feature_id"] = feature["feature_id"]

        if not completed.get("project_type"):
            completed["project_type"] = project["project_type"]

        if not completed.get("feature_name"):
            completed["feature_name"] = feature["feature_name"]

        if not completed.get("target_stack"):
            completed["target_stack"] = project["target_stack"]

        if not completed.get("business_goal"):
            completed["business_goal"] = (
                f"Deliver the {feature['feature_name']} feature for "
                f"the {project['project_type']} application."
            )

        if not completed.get("functional_requirements"):
            completed["functional_requirements"] = [
                feature["feature_description"]
            ]

        if not completed.get("architectural_style"):
            completed["architectural_style"] = "modular"

        return completed


requirement_agent = RequirementAgent()