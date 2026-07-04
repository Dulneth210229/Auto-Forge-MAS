"""
UI/UX Agent component generator.

Purpose:
- Generate one React component at a time (JSX + Tailwind + mock props),
  scoped per-component rather than one giant call for the whole feature --
  smaller, more reliable generations, and a single broken component can be
  retried without regenerating everything else (per the build plan).

Output format is a delimited text format, not JSON: embedding a multi-line
JSX code block inside a JSON string is a common source of escaping failures
with LLMs (unescaped newlines/quotes). Splitting on plain text markers avoids
that failure mode entirely.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.uiux_agent.prompt import (
    COMPONENT_GENERATOR_SYSTEM_PROMPT,
    build_component_generator_user_prompt,
    build_component_repair_prompt,
)
from app.services.llm_provider_service import llm_provider_service

MOCK_PROPS_MARKER = "---MOCK_PROPS_JSON---"
JSX_CODE_MARKER = "---JSX_CODE---"


class ComponentGenerationError(Exception):
    """Raised when a component could not be generated in the required format."""


class UIUXComponentGenerator:
    """
    Generates one component's JSX source + mock props.
    """

    async def generate(
        self,
        project: dict,
        feature: dict,
        page_metadata: dict,
        component_metadata: dict,
        data_entities: list,
        design_system_json: dict,
        ui_preferences: dict,
        human_comment: str | None,
    ) -> tuple[dict[str, Any], str]:
        """
        Returns ({"jsx_code": str, "mock_props": dict}, raw_llm_output).
        """

        provider = llm_provider_service.get_provider()

        prompt = build_component_generator_user_prompt(
            project=project,
            feature=feature,
            page_metadata=page_metadata,
            component_metadata=component_metadata,
            data_entities=data_entities,
            design_system_json=design_system_json,
            ui_preferences=ui_preferences,
            human_comment=human_comment,
        )

        raw_output = await provider.invoke_agent(
            [
                {"role": "system", "content": COMPONENT_GENERATOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )

        try:
            return self._parse(raw_output), raw_output
        except ValueError:
            pass

        repaired_output = await provider.invoke_agent(
            [
                {"role": "system", "content": COMPONENT_GENERATOR_SYSTEM_PROMPT},
                {"role": "user", "content": build_component_repair_prompt(raw_output)},
            ]
        )

        try:
            return self._parse(repaired_output), repaired_output
        except ValueError as error:
            component_name = component_metadata.get("name", "unknown")
            raise ComponentGenerationError(
                f"Component '{component_name}' could not be generated in the required "
                f"format after one repair attempt: {error}"
            ) from error

    def _parse(self, text: str) -> dict[str, Any]:
        if MOCK_PROPS_MARKER not in text or JSX_CODE_MARKER not in text:
            raise ValueError(
                f"Output missing required markers {MOCK_PROPS_MARKER} / {JSX_CODE_MARKER}."
            )

        props_section = text.split(MOCK_PROPS_MARKER, 1)[1].split(JSX_CODE_MARKER, 1)[0].strip()
        jsx_section = text.split(JSX_CODE_MARKER, 1)[1].strip()

        jsx_section = re.sub(r"^```(?:jsx|javascript|js)?\s*", "", jsx_section, flags=re.IGNORECASE)
        jsx_section = re.sub(r"\s*```$", "", jsx_section)

        try:
            mock_props = json.loads(props_section)
        except json.JSONDecodeError as error:
            raise ValueError(f"MOCK_PROPS_JSON section is not valid JSON: {error}") from error

        if not isinstance(mock_props, dict):
            raise ValueError("MOCK_PROPS_JSON section must be a JSON object.")

        if "export default" not in jsx_section:
            raise ValueError("JSX_CODE section must contain 'export default function ComponentName(...)'.")

        return {"jsx_code": jsx_section, "mock_props": mock_props}


uiux_component_generator = UIUXComponentGenerator()
