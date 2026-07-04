"""
Coder Agent planner.

Purpose:
- One-shot LLM call (via llm_provider_service, NOT the agentic model factory --
  this step doesn't need tool calling) that reads the approved SRS,
  Architecture Plan, UI/UX integration manifest, and project manifest, and
  produces code_plan_json: a scoped, traceable list of files to create,
  modify, or delete for exactly one feature.

This plan becomes the task description handed to the agentic coding loop
(M4) -- the loop executes a pre-validated plan rather than improvising
architecture itself.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.coder_agent.prompt import (
    CODE_PLAN_JSON_REPAIR_PROMPT,
    CODE_PLANNER_SYSTEM_PROMPT,
    build_code_plan_repair_prompt,
    build_code_planner_user_prompt,
)
from app.services.llm_provider_service import llm_provider_service


class CodePlanGenerationError(Exception):
    """Raised when the LLM output could not be parsed into code_plan_json."""


class CodePlanner:
    """
    Generates code_plan_json from approved SRS + Architecture Plan + optional
    UI/UX integration manifest + the project's manifest.
    """

    async def generate(
        self,
        project: dict,
        feature: dict,
        srs_json: dict,
        architecture_plan_json: dict,
        ui_integration_manifest_json: dict | None,
        project_manifest_json: dict,
        human_comment: str | None,
        previous_plan_json: dict | None = None,
        validation_feedback: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        """
        Returns (code_plan_json, raw_llm_output).

        previous_plan_json/validation_feedback are set when this is a retry
        after CodePlanValidator rejected an earlier attempt -- the caller
        (CoderAgent.run()) is responsible for the retry loop and budget;
        this method just knows how to build one better-informed attempt.
        """

        provider = llm_provider_service.get_provider()

        prompt = build_code_planner_user_prompt(
            project=project,
            feature=feature,
            srs_json=srs_json,
            architecture_plan_json=architecture_plan_json,
            ui_integration_manifest_json=ui_integration_manifest_json,
            project_manifest_json=project_manifest_json,
            human_comment=human_comment,
            previous_plan_json=previous_plan_json,
            validation_feedback=validation_feedback,
        )

        raw_output = await provider.invoke_agent(
            [
                {"role": "system", "content": CODE_PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )

        try:
            return self._extract_json_object(raw_output), raw_output
        except ValueError:
            pass

        repaired_output = await provider.invoke_agent(
            [
                {"role": "system", "content": CODE_PLAN_JSON_REPAIR_PROMPT},
                {"role": "user", "content": build_code_plan_repair_prompt(raw_output)},
            ]
        )

        try:
            return self._extract_json_object(repaired_output), repaired_output
        except ValueError as error:
            raise CodePlanGenerationError(
                f"Coder Agent planner could not produce valid code_plan_json after one "
                f"repair attempt: {error}"
            ) from error

    def _extract_json_object(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()

        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")

            if start == -1 or end == -1 or end <= start:
                raise ValueError("No JSON object found in Coder Agent planner output.")

            parsed = json.loads(cleaned[start : end + 1])

        if not isinstance(parsed, dict):
            raise ValueError("code_plan_json must be a JSON object.")

        if not isinstance(parsed.get("files"), list) or not parsed["files"]:
            raise ValueError("code_plan_json.files must be a non-empty list.")

        return parsed


code_planner = CodePlanner()
