"""
UI/UX Agent internal schemas.
"""

from pydantic import BaseModel


class UIUXAgentInput(BaseModel):
    """
    Internal input passed to UIUXAgent.

    Mirrors ArchitectureAgentInput's shape: the agent receives already-loaded
    context (not artifact IDs) so it does not need to know how those artifacts
    were located.
    """

    project: dict
    feature: dict
    srs_json: dict
    enhanced_srs_json: dict | None = None
    architecture_plan_json: dict
    design_system_json: dict
    ui_preferences: dict = {}
    human_comment: str | None = None


class UIUXAgentOutput(BaseModel):
    """
    Internal output produced by UIUXAgent.

    ui_metadata_json:
        Validated design-tokens + page/component tree, coverage-checked
        against the approved SRS.

    component_files:
        component name -> generated .jsx source text.

    page_screenshots:
        page_id -> PNG bytes (one screenshot per page, all of that page's
        components rendered together).

    integration_manifest_json:
        Deterministic route/nav/prop manifest for the future Coder Agent.

    ui_design_markdown:
        Human-readable summary for the approval reviewer.

    raw_llm_output:
        Original ui_metadata_json LLM output, for debugging.
    """

    ui_metadata_json: dict
    component_files: dict[str, str] = {}
    page_screenshots: dict[str, bytes] = {}
    integration_manifest_json: dict = {}
    ui_design_markdown: str = ""
    raw_llm_output: str
    artifact_ids: list[str] = []
