"""
UI/UX Agent metadata modeler.

Purpose:
- Ask the LLM (one-shot, via the existing llm_provider_service -- no tool
  calling needed) for ui_metadata_json.
- Parse and lightly repair its output.

This mirrors architecture_agent's JSON-extraction/repair pattern: try once,
repair once on failure, then give up and let the caller decide (the UI/UX
Agent fails loudly rather than synthesizing a fallback here, since a
guessed-at UI plan is more likely to be actively wrong than merely absent).
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.uiux_agent.prompt import (
    UIUX_METADATA_SYSTEM_PROMPT,
    UIUX_JSON_REPAIR_PROMPT,
    build_uiux_json_repair_prompt,
    build_uiux_metadata_user_prompt,
)
from app.services.llm_provider_service import llm_provider_service


class UIMetadataGenerationError(Exception):
    """Raised when the LLM output could not be parsed into ui_metadata_json."""


class UIUXMetadataModeler:
    """
    Generates ui_metadata_json from approved SRS + Architecture Plan + the
    project's existing design system.
    """

    async def generate(
        self,
        project: dict,
        feature: dict,
        srs_json: dict,
        enhanced_srs_json: dict | None,
        architecture_plan_json: dict,
        design_system_json: dict,
        ui_preferences: dict,
        human_comment: str | None,
    ) -> tuple[dict[str, Any], str]:
        """
        Returns (ui_metadata_json, raw_llm_output).
        """

        provider = llm_provider_service.get_provider()

        prompt = build_uiux_metadata_user_prompt(
            project=project,
            feature=feature,
            srs_json=srs_json,
            enhanced_srs_json=enhanced_srs_json,
            architecture_plan_json=architecture_plan_json,
            design_system_json=design_system_json,
            ui_preferences=ui_preferences,
            human_comment=human_comment,
        )

        raw_output = await provider.invoke_agent(
            [
                {"role": "system", "content": UIUX_METADATA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )

        try:
            return self._extract_json_object(raw_output), raw_output
        except ValueError:
            pass

        repair_prompt = build_uiux_json_repair_prompt(raw_output)

        repaired_output = await provider.invoke_agent(
            [
                {"role": "system", "content": UIUX_JSON_REPAIR_PROMPT},
                {"role": "user", "content": repair_prompt},
            ]
        )

        try:
            return self._extract_json_object(repaired_output), repaired_output
        except ValueError as error:
            raise UIMetadataGenerationError(
                f"UI/UX Agent could not produce valid ui_metadata_json after one repair attempt: {error}"
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
                raise ValueError("No JSON object found in UI/UX Agent output.")

            parsed = json.loads(cleaned[start : end + 1])

        if not isinstance(parsed, dict):
            raise ValueError("UI/UX Agent output must be a JSON object.")

        if not isinstance(parsed.get("pages"), list) or not parsed["pages"]:
            raise ValueError("ui_metadata_json.pages must be a non-empty list.")

        return parsed
