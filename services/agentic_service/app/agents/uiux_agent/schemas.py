"""
UI/UX Agent Schemas.

These schemas define the input/output contract for the UI/UX Agent.

Important:
- The UI/UX Agent is not a simple mockup generator anymore.
- It is a frontend task execution agent.
- It reads approved artifacts and the architecture implementation plan.
- It executes only tasks assigned to "uiux_agent".
- It writes real React + Tailwind files into the shared staging workspace.
- It returns patch-based file changes, not uncontrolled random files.

These schemas are used by:
- uiux_agent/agent.py
- uiux_agent/task_runner.py
- uiux_agent/prompt.py
- API request/response models
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------
# UI preference schemas
# ---------------------------------------------------------------------


class UIPreferences(BaseModel):
    """
    User-provided UI preferences.

    These preferences are optional. If the user does not provide them,
    the UI/UX Agent should use professional enterprise SaaS defaults.
    """

    theme: str | None = Field(
        default="modern light",
        description="Preferred theme style. Example: modern dark, modern light, enterprise SaaS.",
    )
    primary_color: str | None = Field(
        default="blue",
        description="Preferred primary color. Example: blue, emerald, purple.",
    )
    layout: str | None = Field(
        default="clean responsive layout",
        description="Preferred layout style. Example: centered card, dashboard layout.",
    )
    responsive: bool = Field(
        default=True,
        description="Whether the UI should be responsive.",
    )
    mobile_first: bool = Field(
        default=True,
        description="Whether the UI should follow mobile-first design.",
    )
    include_remember_me: bool | None = Field(
        default=None,
        description="Whether auth-related screens should include remember-me.",
    )
    include_forgot_password: bool | None = Field(
        default=None,
        description="Whether auth-related screens should include forgot password.",
    )
    accessibility_level: str | None = Field(
        default="standard",
        description="Accessibility expectation. Example: standard, high.",
    )
    branding_text: str | None = Field(
        default=None,
        description="Optional brand text to show in UI.",
    )
    additional_notes: str | None = Field(
        default=None,
        description="Any extra human UI preferences.",
    )


class UIUXAgentRunRequest(BaseModel):
    """
    API request body for running the UI/UX Agent.

    This is used by the route:
        POST /features/{feature_id}/agents/uiux/run
    """

    human_comment: str | None = Field(
        default=None,
        description="Optional human instruction for this UI/UX run.",
    )
    ui_preferences: UIPreferences = Field(
        default_factory=UIPreferences,
        description="User UI preferences.",
    )
    reset_staging: bool = Field(
        default=False,
        description="If true, staging workspace can be reset before generation. Use carefully.",
    )


# ---------------------------------------------------------------------
# Artifact and task schemas
# ---------------------------------------------------------------------


class ArtifactReference(BaseModel):
    """
    Reference to an approved artifact.

    The task runner can use file_path to read approved artifact content.
    """

    artifact_id: str | None = Field(default=None)
    artifact_type: str = Field(..., description="Example: SRS, SDS, API_CONTRACT.")
    file_path: str = Field(..., description="Path to the artifact file.")
    version: int | None = Field(default=None)
    approval_status: str | None = Field(default=None)


class UIUXExecutionTask(BaseModel):
    """
    One frontend task assigned to the UI/UX Agent.

    The Architecture Agent should ideally generate these tasks inside
    implementation_plan_v1.json.

    If the Architecture Agent does not generate this exact structure yet,
    the UI/UX task runner can create a fallback task from the approved
    architecture plan.
    """

    task_id: str = Field(..., description="Stable task ID. Example: LOGIN-FE-001.")
    title: str = Field(..., description="Short task title.")
    owner_agent: Literal["uiux_agent"] = Field(
        default="uiux_agent",
        description="UI/UX Agent must only execute tasks owned by uiux_agent.",
    )
    task_type: str = Field(
        default="frontend_create",
        description="Example: frontend_create, frontend_modify, frontend_refactor.",
    )
    priority: int = Field(default=999)
    description: str | None = Field(default=None)
    files_to_create: list[str] = Field(default_factory=list)
    files_to_modify: list[str] = Field(default_factory=list)
    expected_files: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    acceptance_checks: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    design_notes: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class UIUXAgentInput(BaseModel):
    """
    Internal input passed into the UI/UX Agent.

    This is normally built by agent.py after loading:
    - project
    - feature
    - approved artifacts
    - implementation tasks
    - UI preferences
    """

    project: dict[str, Any]
    feature: dict[str, Any]
    approved_artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary of artifact name to file path.",
    )
    ui_preferences: UIPreferences = Field(default_factory=UIPreferences)
    human_comment: str | None = None
    implementation_tasks: list[UIUXExecutionTask] = Field(default_factory=list)
    reset_staging: bool = False


# ---------------------------------------------------------------------
# Patch schemas
# ---------------------------------------------------------------------


PatchChangeType = Literal[
    "create_directory",
    "create_file",
    "modify_file",
    "append_to_file",
    "replace_section",
    "update_json_field",
]


class UIUXPatchRequest(BaseModel):
    """
    Patch request generated by the LLM and applied by patch_service.

    The LLM should not directly write files.
    It should return patch-ready JSON.
    The backend validates and applies patches safely.
    """

    task_id: str = Field(..., description="Task ID this patch belongs to.")
    file_path: str = Field(
        ...,
        description=(
            "Path relative to staging workspace. "
            "For UI/UX Agent this should usually start with frontend/."
        ),
    )
    change_type: PatchChangeType = Field(...)

    description: str = Field(
        default="",
        description="Short explanation of the file change.",
    )
    purpose: str = Field(
        default="",
        description="Purpose of the file in the generated app.",
    )

    # Used for create_file and modify_file.
    content: str | None = Field(default=None)

    # Used for replace_section.
    old_text: str | None = Field(default=None)
    new_text: str | None = Field(default=None)

    # Used for update_json_field.
    json_path: str | None = Field(default=None)
    value: Any | None = Field(default=None)


class UIPatchRecord(BaseModel):
    """
    Patch record after applying a patch.

    This is usually returned by patch_service.
    """

    patch_id: str
    project_id: str
    feature_id: str
    task_id: str | None = None
    agent_name: str = "uiux_agent"
    file_path: str
    change_type: str
    description: str | None = None
    purpose: str | None = None
    workspace: str = "staging"
    status: str
    error_message: str | None = None
    created_at: str
    applied_at: str | None = None


# ---------------------------------------------------------------------
# LLM output schema
# ---------------------------------------------------------------------


class UIUXDeviationRequest(BaseModel):
    """
    Deviation request returned by the LLM when it cannot safely execute a task
    inside the approved architecture plan.

    Example:
    The UI preferences ask for a "forgot password" link but the approved plan
    does not include it.
    """

    reason: str
    suggested_change: str
    impact: str
    severity: Literal["low", "medium", "high"] = "medium"
    requires_human_approval: bool = True


class UIUXTaskLLMOutput(BaseModel):
    """
    Strict JSON structure that the LLM must return for one UI/UX task.

    The task runner will parse this JSON.
    Then patch_service will apply the patches.
    """

    task_id: str
    task_status: Literal[
        "completed",
        "failed",
        "requires_human_review",
    ] = "completed"

    summary: str = Field(
        ...,
        description="Short description of what the task output contains.",
    )
    files_to_create: list[str] = Field(default_factory=list)
    files_to_modify: list[str] = Field(default_factory=list)
    patches: list[UIUXPatchRequest] = Field(default_factory=list)

    important_decisions: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)

    deviation_request: UIUXDeviationRequest | None = None


# ---------------------------------------------------------------------
# Task execution results and memory
# ---------------------------------------------------------------------


class UIUXTaskExecutionResult(BaseModel):
    """
    Result of executing one UI/UX task.
    """

    task_id: str
    title: str | None = None
    status: Literal[
        "completed",
        "failed",
        "requires_human_review",
    ]
    summary: str | None = None
    patches: list[UIPatchRecord] = Field(default_factory=list)
    validation_result: dict[str, Any] | None = None
    deviation_request: dict[str, Any] | None = None
    error_message: str | None = None


class UIUXTaskMemory(BaseModel):
    """
    Structured UI/UX Agent memory.

    This is saved to:
        memory/{project_slug}/features/{feature_slug}/uiux_memory.json

    A copy can also be saved into:
        outputs/{project_slug}/{feature_slug}/04_uiux/uiux_task_memory_v1.json
    """

    project_id: str
    feature_id: str
    agent_name: Literal["uiux_agent"] = "uiux_agent"
    memory_version: int = 1
    last_updated: str | None = None
    completed_tasks: list[dict[str, Any]] = Field(default_factory=list)
    failed_tasks: list[dict[str, Any]] = Field(default_factory=list)
    pending_tasks: list[str] = Field(default_factory=list)
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    patch_ids: list[str] = Field(default_factory=list)
    commands_requested: list[dict[str, Any]] = Field(default_factory=list)
    validation_results: list[dict[str, Any]] = Field(default_factory=list)
    important_decisions: list[dict[str, Any]] = Field(default_factory=list)
    next_recommended_task: str | None = None


# ---------------------------------------------------------------------
# Manifest and final output schemas
# ---------------------------------------------------------------------


class FrontendManifestFile(BaseModel):
    """
    One frontend file created or modified by the UI/UX Agent.
    """

    path: str
    action: Literal["created", "modified"]
    purpose: str
    task_id: str | None = None


class FrontendManifest(BaseModel):
    """
    Frontend manifest generated after the UI/UX Agent completes.

    This tells the Coder Agent what frontend files exist and what they do.
    """

    project_id: str
    feature_id: str
    agent_name: Literal["uiux_agent"] = "uiux_agent"
    generated_stack: str = "React + Tailwind CSS"
    workspace: str = "staging"
    frontend_root: str
    files: list[FrontendManifestFile] = Field(default_factory=list)
    run_notes: list[str] = Field(default_factory=list)
    integration_notes_for_coder: list[str] = Field(default_factory=list)
    created_at: str | None = None


class UIUXAgentOutput(BaseModel):
    """
    Final output returned by the UI/UX Agent.
    """

    project_id: str
    feature_id: str
    agent_name: Literal["uiux_agent"] = "uiux_agent"
    status: Literal["completed", "failed", "requires_human_review"]
    message: str
    task_results: list[UIUXTaskExecutionResult] = Field(default_factory=list)

    artifact_paths: dict[str, str] = Field(default_factory=dict)
    workspace_paths: dict[str, str] = Field(default_factory=dict)

    frontend_manifest: FrontendManifest | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------
# Backward compatibility aliases
# ---------------------------------------------------------------------
# These aliases help if older code imports these names.
# They can be removed later after the full refactor is complete.

UIUXInput = UIUXAgentInput
UIUXOutput = UIUXAgentOutput
UIUXTask = UIUXExecutionTask