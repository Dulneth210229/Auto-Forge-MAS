"""
Coder Agent LLM response parser.

Purpose:
    Parse and validate the raw LLM response into a typed CoderAgentOutput model.

Architecture fit:
    - Called by agent.py immediately after provider.generate() returns.
    - Uses json_utils.extract_json_object() for robust JSON extraction.
    - Validates all required top-level keys before constructing Pydantic models.
    - Raises ValueError with descriptive messages on any parse failure.

Why this module is necessary:
    LLMs may return:
    1. Pure JSON
    2. JSON wrapped in markdown code fences (```json ... ```)
    3. JSON preceded by explanation text
    4. JSON with trailing notes
    5. Partially formed JSON on timeout

    The parser handles all these cases gracefully rather than crashing.

Author: Coder Agent (Auto-Forge MAS)
Version: 1.0.0
"""

from typing import Any

from app.agents.coder_agent.schemas import (
    CoderAgentOutput,
    GeneratedFile,
    EnvVarRequirement,
    RequirementCodeMapping,
    ArtifactMetadataEntry,
)
from app.utils.json_utils import extract_json_object
from app.utils.logger import get_logger

logger = get_logger("coder_agent.parser")

# ---------------------------------------------------------------------------
# Required top-level keys in the LLM JSON output.
# The parser validates these before attempting model construction.
# ---------------------------------------------------------------------------
_REQUIRED_KEYS = [
    "generated_files",
    "updated_files",
    "unchanged_files",
    "env_vars_required",
    "run_commands",
    "integration_notes",
    "requirement_mapping",
    "setup_instructions_markdown",
    "merge_report_markdown",
]


def parse_coder_agent_response(
    raw_response: str,
    feature_id: str,
    feature_name: str,
    project_id: str,
    project_name: str,
    target_stack: str,
    version: int,
) -> CoderAgentOutput:
    """
    Parse the raw LLM string response into a CoderAgentOutput model.

    Steps:
    1. Extract JSON from the raw response (handles markdown fences, preamble).
    2. Validate that all required top-level keys are present.
    3. Parse each file list into GeneratedFile models.
    4. Parse env_vars_required into EnvVarRequirement models.
    5. Parse requirement_mapping into RequirementCodeMapping models.
    6. Build the ArtifactMetadataEntry.
    7. Build the file_tree using project_merger if not provided by LLM.
    8. Return the fully validated CoderAgentOutput.

    Args:
        raw_response:  Raw string from provider.generate().
        feature_id:    Current feature ID (used to stamp files).
        feature_name:  Current feature name.
        project_id:    Current project ID.
        project_name:  Current project name.
        target_stack:  Technology stack.
        version:       Artifact version number for this run.

    Returns:
        Validated CoderAgentOutput.

    Raises:
        ValueError: If the response cannot be parsed or required keys are missing.
    """
    logger.info("[Parser] Parsing Coder Agent LLM response (%d chars).", len(raw_response))

    # ------------------------------------------------------------------
    # Step 1: Extract JSON
    # ------------------------------------------------------------------
    try:
        data = extract_json_object(raw_response)
    except ValueError as exc:
        raise ValueError(
            f"Coder Agent: Failed to extract JSON from LLM response. "
            f"Detail: {exc}\n\n"
            f"Raw response (first 500 chars):\n{raw_response[:500]}"
        ) from exc

    logger.info("[Parser] JSON extracted successfully. Validating structure.")

    # ------------------------------------------------------------------
    # Step 2: Validate required keys
    # ------------------------------------------------------------------
    missing_keys = [key for key in _REQUIRED_KEYS if key not in data]
    if missing_keys:
        raise ValueError(
            f"Coder Agent: LLM response JSON is missing required keys: {missing_keys}. "
            f"Present keys: {list(data.keys())}"
        )

    # ------------------------------------------------------------------
    # Step 3: Parse file lists
    # ------------------------------------------------------------------
    generated_files = _parse_file_list(
        data.get("generated_files", []),
        expected_change_type="new",
        feature_id=feature_id,
        version=version,
        context="generated_files",
    )

    updated_files = _parse_file_list(
        data.get("updated_files", []),
        expected_change_type="updated",
        feature_id=feature_id,
        version=version,
        context="updated_files",
    )

    unchanged_files = _parse_file_list(
        data.get("unchanged_files", []),
        expected_change_type="unchanged",
        feature_id=feature_id,
        version=version,
        context="unchanged_files",
    )

    # ------------------------------------------------------------------
    # Step 4: Parse env vars
    # ------------------------------------------------------------------
    env_vars_required = _parse_env_vars(data.get("env_vars_required", []))

    # ------------------------------------------------------------------
    # Step 5: Parse requirement mapping
    # ------------------------------------------------------------------
    requirement_mapping = _parse_requirement_mapping(
        data.get("requirement_mapping", [])
    )

    # ------------------------------------------------------------------
    # Step 6: Parse scalar fields
    # ------------------------------------------------------------------
    run_commands = _ensure_string_list(data.get("run_commands", []), "run_commands")
    integration_notes = _ensure_string_list(
        data.get("integration_notes", []), "integration_notes"
    )
    setup_instructions_markdown = str(
        data.get("setup_instructions_markdown", "")
    ).strip()
    merge_report_markdown = str(
        data.get("merge_report_markdown", "")
    ).strip()

    # ------------------------------------------------------------------
    # Step 7: Build or retrieve file_tree
    # ------------------------------------------------------------------
    file_tree = data.get("file_tree")
    if not file_tree or not isinstance(file_tree, dict):
        # Build the tree from the parsed file lists
        from app.agents.coder_agent.project_merger import project_merger
        all_files = generated_files + updated_files + unchanged_files
        file_tree = project_merger.build_file_tree(all_files)
        logger.info("[Parser] file_tree not provided by LLM — built from parsed files.")

    # ------------------------------------------------------------------
    # Step 8: Build ArtifactMetadataEntry
    # ------------------------------------------------------------------
    artifact_metadata = ArtifactMetadataEntry(
        agent="coder_agent",
        feature_id=feature_id,
        feature_name=feature_name,
        project_id=project_id,
        project_name=project_name,
        version=version,
        target_stack=target_stack,
        generated_files_count=len(generated_files),
        updated_files_count=len(updated_files),
        unchanged_files_count=len(unchanged_files),
    )

    logger.info(
        "[Parser] Parse complete. New: %d, Updated: %d, Unchanged: %d, EnvVars: %d.",
        len(generated_files),
        len(updated_files),
        len(unchanged_files),
        len(env_vars_required),
    )

    return CoderAgentOutput(
        file_tree=file_tree,
        generated_files=generated_files,
        updated_files=updated_files,
        unchanged_files=unchanged_files,
        env_vars_required=env_vars_required,
        run_commands=run_commands,
        integration_notes=integration_notes,
        requirement_mapping=requirement_mapping,
        artifact_metadata=artifact_metadata,
        setup_instructions_markdown=setup_instructions_markdown,
        merge_report_markdown=merge_report_markdown,
    )


# ---------------------------------------------------------------------------
# Private helper functions
# ---------------------------------------------------------------------------

def _parse_file_list(
    raw_list: Any,
    expected_change_type: str,
    feature_id: str,
    version: int,
    context: str,
) -> list[GeneratedFile]:
    """
    Parse a raw list of file dicts into GeneratedFile models.

    Args:
        raw_list:             The raw value from the LLM JSON (should be a list).
        expected_change_type: "new", "updated", or "unchanged".
        feature_id:           Current feature ID for stamping.
        version:              Current artifact version for stamping.
        context:              Key name (for error messages).

    Returns:
        List of GeneratedFile instances.
    """
    if not isinstance(raw_list, list):
        logger.warning(
            "[Parser] '%s' is not a list (got %s). Treating as empty.",
            context, type(raw_list).__name__
        )
        return []

    result: list[GeneratedFile] = []

    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            logger.warning("[Parser] Skipping non-dict item at %s[%d].", context, i)
            continue

        try:
            # Enforce the correct change_type regardless of what the LLM returned
            item["change_type"] = expected_change_type
            item.setdefault("feature_id", feature_id)
            item.setdefault("version", version)
            item.setdefault("purpose", "Generated by Coder Agent.")
            item.setdefault("description", f"File for the {expected_change_type} category.")

            file_obj = GeneratedFile(**item)
            result.append(file_obj)

        except Exception as exc:
            logger.warning(
                "[Parser] Failed to parse file at %s[%d]: %s. Item: %s",
                context, i, exc, str(item)[:200]
            )

    return result


def _parse_env_vars(raw_list: Any) -> list[EnvVarRequirement]:
    """
    Parse the env_vars_required list from the LLM JSON.

    Handles both dict format and plain string format.
    """
    if not isinstance(raw_list, list):
        return []

    result: list[EnvVarRequirement] = []

    for i, item in enumerate(raw_list):
        try:
            if isinstance(item, str):
                result.append(EnvVarRequirement(
                    name=item.upper().strip(),
                    description=f"Required environment variable: {item}",
                    example_value="your-value-here",
                    required=True,
                ))
            elif isinstance(item, dict):
                item.setdefault("example_value", "your-value-here")
                item.setdefault("required", True)
                result.append(EnvVarRequirement(**item))
        except Exception as exc:
            logger.warning("[Parser] Failed to parse env_var at index %d: %s", i, exc)

    return result


def _parse_requirement_mapping(raw_list: Any) -> list[RequirementCodeMapping]:
    """
    Parse the requirement_mapping list from the LLM JSON.
    """
    if not isinstance(raw_list, list):
        return []

    result: list[RequirementCodeMapping] = []

    for i, item in enumerate(raw_list):
        try:
            if isinstance(item, dict):
                item.setdefault("requirement_text", "")
                item.setdefault("file_paths", [])
                result.append(RequirementCodeMapping(**item))
        except Exception as exc:
            logger.warning(
                "[Parser] Failed to parse requirement_mapping at index %d: %s", i, exc
            )

    return result


def _ensure_string_list(value: Any, context: str) -> list[str]:
    """
    Ensure a value is a list of strings.

    If the LLM returned a plain string instead of a list, wrap it.
    """
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str) and value.strip():
        logger.warning(
            "[Parser] '%s' is a plain string — wrapping in a list.", context
        )
        return [value.strip()]
    return []
