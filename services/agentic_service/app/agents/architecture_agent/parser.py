"""
Architecture Agent output parser.

The LLM is instructed to return valid JSON.

However, LLMs sometimes return:
- markdown before JSON
- JSON inside code fences
- small formatting mistakes

This parser extracts the required Architecture Agent fields.
"""

from app.agents.architecture_agent.schemas import ArchitectureAgentOutput
from app.utils.json_utils import extract_json_from_text


REQUIRED_ARCHITECTURE_KEYS = {
    "sds_markdown",
    "sds_json",
    "usecase_puml",
    "traceability_json",
}


def parse_architecture_agent_response(raw_response: str) -> ArchitectureAgentOutput:
    """
    Parse and validate the Architecture Agent LLM response.

    Args:
        raw_response:
            Raw text returned from the LLM provider.

    Returns:
        ArchitectureAgentOutput

    Raises:
        ValueError:
            If required fields are missing.
    """
    parsed_json = extract_json_from_text(raw_response)

    missing_keys = REQUIRED_ARCHITECTURE_KEYS - set(parsed_json.keys())

    if missing_keys:
        raise ValueError(
            f"Architecture Agent response is missing required keys: {missing_keys}"
        )

    usecase_puml = parsed_json["usecase_puml"]

    if "@startuml" not in usecase_puml or "@enduml" not in usecase_puml:
        raise ValueError(
            "Invalid PlantUML output. usecase_puml must include @startuml and @enduml."
        )

    return ArchitectureAgentOutput(
        sds_markdown=parsed_json["sds_markdown"],
        sds_json=parsed_json["sds_json"],
        usecase_puml=usecase_puml,
        traceability_json=parsed_json["traceability_json"],
    )