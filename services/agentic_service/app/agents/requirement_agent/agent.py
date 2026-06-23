"""
Requirement Agent.

Purpose:
- Generate initial SRS for one feature.
- Ask LLM to generate JSON only.
- Convert JSON to Markdown inside Requirement Agent.
- Save both JSON and Markdown artifacts.
- Keep all logic Requirement-Agent-specific.

This file does not change:
- LLM provider
- shared markdown utilities
- other agents
"""

import json
import re
from typing import Any

from app.agents.requirement_agent.markdown_builder import RequirementSRSMarkdownBuilder
from app.agents.requirement_agent.prompt import (
    JSON_REPAIR_PROMPT,
    REQUIREMENT_AGENT_SYSTEM_PROMPT,
    build_json_repair_prompt,
    build_requirement_user_prompt,
)
from app.agents.requirement_agent.schemas import RequirementAgentOutput
from app.core.enums import AgentName, ArtifactFormat, ArtifactType, FeatureStatus
from app.schemas.agent_schema import AgentRunResponse
from app.schemas.requirement_schema import RequirementAgentRunRequest
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.llm_provider_service import llm_provider_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequirementAgent:
    """
    Main Requirement Agent class.

    This class controls the full Requirement Agent process:
    1. Read project and feature.
    2. Read BA input.
    3. Call LLM.
    4. Parse JSON.
    5. Build Markdown from JSON.
    6. Save artifacts.
    """

    REQUIRED_KEYS = [
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

    def __init__(self):
        """
        Initialize Requirement Agent dependencies.

        markdown_builder:
            Agent-specific builder used to convert SRS JSON into SRS Markdown.
        """
        self.markdown_builder = RequirementSRSMarkdownBuilder()

    async def run(self, feature_id: str, request: RequirementAgentRunRequest) -> AgentRunResponse:
        """
        Run the Requirement Agent.

        This method is called from:
            POST /features/{feature_id}/agents/requirement/run
        """

        logger.info("Requirement Agent started for feature_id=%s", feature_id)

        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])

        if not project:
            raise ValueError("Project not found for this feature.")

        # Update feature state.
        feature["feature_status"] = FeatureStatus.IN_PROGRESS
        feature["current_agent"] = AgentName.REQUIREMENT

        # Convert Pydantic request body to normal Python dictionary.
        ba_input = request.ba_input.model_dump(mode="json")

        # Fill missing values using project and feature data.
        ba_input = self._complete_ba_input(
            project=project,
            feature=feature,
            ba_input=ba_input
        )

        # Generate SRS JSON using LLM.
        output = await self._generate_requirement_output(
            project=project,
            feature=feature,
            ba_input=ba_input,
            human_comment=request.human_comment
        )

        # Save Markdown artifact.
        markdown_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename="SRS_v{version}.md",
            content=output.srs_markdown
        )

        # Save JSON artifact.
        # Note:
        # If your artifact service does not support grouped versions,
        # this may become SRS_v2.json after SRS_v1.md.
        # That is acceptable for now because we are avoiding shared file changes.
        json_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS,
            filename="SRS_v{version}.json",
            data=output.srs_json
        )

        logger.info(
            "Requirement Agent completed. artifacts=%s",
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

    async def _generate_requirement_output(
        self,
        project: dict,
        feature: dict,
        ba_input: dict,
        human_comment: str | None
    ) -> RequirementAgentOutput:
        """
        Generate SRS output.

        Main approach:
        - Ask LLM for JSON only.
        - Try to parse JSON.
        - If parsing fails, ask LLM to repair JSON.
        - If repair fails, create fallback SRS JSON from BA input.
        - Convert final JSON to Markdown.
        """

        provider = llm_provider_service.get_provider()

        prompt = build_requirement_user_prompt(
            project=project,
            feature=feature,
            ba_input=ba_input,
            human_comment=human_comment
        )

        raw_output = await provider.invoke_agent([
            {
                "role": "system",
                "content": REQUIREMENT_AGENT_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ])

        try:
            srs_json = self._parse_and_validate_json(raw_output)

        except Exception as first_error:
            logger.warning("Initial SRS JSON parse failed: %s", first_error)

            repair_prompt = build_json_repair_prompt(raw_output)

            repaired_output = await provider.invoke_agent([
                {
                    "role": "system",
                    "content": JSON_REPAIR_PROMPT
                },
                {
                    "role": "user",
                    "content": repair_prompt
                }
            ])

            try:
                srs_json = self._parse_and_validate_json(repaired_output)
                raw_output = repaired_output

            except Exception as second_error:
                logger.warning("JSON repair failed: %s", second_error)

                # Final safe fallback.
                # This prevents the agent from failing completely.
                srs_json = self._build_fallback_srs_json(
                    project=project,
                    feature=feature,
                    ba_input=ba_input,
                    reason=str(second_error)
                )

                raw_output = json.dumps(srs_json, indent=2)

        srs_markdown = self.markdown_builder.build(srs_json)

        return RequirementAgentOutput(
            srs_json=srs_json,
            srs_markdown=srs_markdown,
            raw_llm_output=raw_output
        )

    def _parse_and_validate_json(self, raw_output: str) -> dict:
        """
        Parse and validate LLM JSON output.

        This method is kept inside Requirement Agent to avoid changing
        shared/common JSON utilities.
        """

        parsed = self._extract_json_object(raw_output)

        # If the model returns {"srs_json": {...}}, accept it.
        if "srs_json" in parsed and isinstance(parsed["srs_json"], dict):
            parsed = parsed["srs_json"]

        missing = [key for key in self.REQUIRED_KEYS if key not in parsed]

        if missing:
            raise ValueError(f"Missing required SRS keys: {missing}")

        self._validate_stable_ids(parsed)

        return parsed

    def _extract_json_object(self, text: str) -> dict:
        """
        Extract a JSON object from LLM output.

        This is Requirement-Agent-specific.
        It does not change shared json_utils.py.
        """

        cleaned = text.strip()

        # Remove markdown fences if the model used them accidentally.
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in LLM output.")

        possible_json = cleaned[start:end + 1]

        return json.loads(possible_json)

    def _validate_stable_ids(self, srs_json: dict) -> None:
        """
        Validate stable IDs in key requirement sections.

        Stable IDs are needed for traceability across agents.
        """

        sections = [
            "functional_requirements",
            "non_functional_requirements",
            "acceptance_criteria",
        ]

        for section_name in sections:
            section = srs_json.get(section_name, [])

            if not isinstance(section, list) or not section:
                raise ValueError(f"{section_name} must be a non-empty list.")

            for index, item in enumerate(section):
                if not isinstance(item, dict):
                    raise ValueError(f"{section_name}[{index}] must be an object.")

                if not item.get("id"):
                    raise ValueError(f"{section_name}[{index}] missing id.")

                if not item.get("description"):
                    raise ValueError(f"{section_name}[{index}] missing description.")

    def _complete_ba_input(
        self,
        project: dict,
        feature: dict,
        ba_input: dict
    ) -> dict:
        """
        Fill missing BA input using project and feature metadata.
        """

        completed = dict(ba_input)

        completed["project_id"] = project["project_id"]
        completed["project_name"] = project["project_name"]
        completed["feature_id"] = feature["feature_id"]

        completed.setdefault("project_type", project["project_type"])
        completed.setdefault("feature_name", feature["feature_name"])
        completed.setdefault("target_stack", project["target_stack"])
        completed.setdefault("architectural_style", "modular")

        if not completed.get("business_goal"):
            completed["business_goal"] = (
                f"Deliver the {feature['feature_name']} feature "
                f"for the {project['project_type']} application."
            )

        if not completed.get("functional_requirements"):
            completed["functional_requirements"] = [
                feature["feature_description"]
            ]

        return completed

    def _build_fallback_srs_json(
        self,
        project: dict,
        feature: dict,
        ba_input: dict,
        reason: str
    ) -> dict:
        """
        Build fallback SRS JSON if LLM JSON generation fails.

        Why:
        This prevents the Requirement Agent from completely failing.
        The fallback is basic but valid and reviewable by the human.
        """

        functional_requirements = self._make_requirement_items(
            prefix="FR",
            items=ba_input.get("functional_requirements", [])
        )

        non_functional_requirements = self._make_requirement_items(
            prefix="NFR",
            items=ba_input.get("non_functional_requirements", []),
            extra_key="category",
            extra_value="General"
        )

        acceptance_criteria = self._make_requirement_items(
            prefix="AC",
            items=ba_input.get("acceptance_criteria", [])
        )

        if not acceptance_criteria:
            acceptance_criteria = [
                {
                    "id": "AC-001",
                    "description": "The feature must satisfy the approved functional requirements."
                }
            ]

        return {
            "project_id": project["project_id"],
            "project_name": project["project_name"],
            "project_type": project["project_type"],
            "feature_id": feature["feature_id"],
            "feature_name": feature["feature_name"],
            "target_stack": ba_input.get("target_stack", project["target_stack"]),
            "architectural_style": ba_input.get("architectural_style", "modular"),
            "business_goal": ba_input.get("business_goal", ""),
            "scope": [
                f"Implement the {feature['feature_name']} feature only."
            ],
            "out_of_scope": [
                "Unrelated features are not included in this iteration."
            ],
            "user_roles": ba_input.get("user_roles", []),
            "functional_requirements": functional_requirements,
            "non_functional_requirements": non_functional_requirements,
            "user_stories": self._make_user_stories(ba_input),
            "acceptance_criteria": acceptance_criteria,
            "input_requirements": ba_input.get("data_requirements", []),
            "output_requirements": [
                "The system should return a clear success or failure response."
            ],
            "ui_expectations": ba_input.get("ui_expectations", []),
            "api_expectations": ba_input.get("api_expectations", []),
            "data_requirements": ba_input.get("data_requirements", []),
            "validation_rules": [
                {
                    "id": "VR-001",
                    "description": "Input values must be validated before processing."
                }
            ],
            "constraints": ba_input.get("constraints", []),
            "assumptions": ba_input.get("assumptions", []) + [
                f"Fallback SRS was generated because LLM JSON parsing failed: {reason}"
            ],
            "risks": [
                "Fallback SRS may need human refinement before approval."
            ],
            "dependencies": [],
            "traceability": [
                {
                    "requirement_id": "FR-001",
                    "related_acceptance_criteria": ["AC-001"],
                    "notes": "Generated by fallback SRS builder."
                }
            ]
        }

    def _make_requirement_items(
        self,
        prefix: str,
        items: list[str],
        extra_key: str | None = None,
        extra_value: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Convert simple strings into requirement objects with stable IDs.
        """

        result = []

        for index, item in enumerate(items, start=1):
            record = {
                "id": f"{prefix}-{index:03d}",
                "description": item
            }

            if prefix == "FR":
                record["priority"] = "Must Have"

            if extra_key and extra_value:
                record[extra_key] = extra_value

            result.append(record)

        return result

    def _make_user_stories(self, ba_input: dict) -> list[dict[str, str]]:
        """
        Generate basic user stories from user roles.
        """

        roles = ba_input.get("user_roles", []) or ["User"]
        feature_name = ba_input.get("feature_name", "feature")

        stories = []

        for index, role in enumerate(roles, start=1):
            stories.append({
                "id": f"US-{index:03d}",
                "role": role,
                "goal": f"use the {feature_name} feature",
                "benefit": "complete the intended business process"
            })

        return stories


requirement_agent = RequirementAgent()