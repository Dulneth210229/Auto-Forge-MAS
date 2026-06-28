"""
Coder Agent internal schemas.

Purpose:
    Define all Pydantic data models used exclusively within the Coder Agent.

Architecture fit:
    These schemas form the contract between the Coder Agent's internal modules.
    The API route uses CoderAgentInput to pass context in, and receives
    CoderAgentOutput back — which it then saves as versioned artifacts.

Other modules that use this file:
    - agent.py            (constructs CoderAgentInput, receives CoderAgentOutput)
    - context_builder.py  (populates artifact content fields on CoderAgentInput)
    - env_validator.py    (reads EnvVarRequirement list from CoderAgentOutput)
    - project_merger.py   (reads/writes GeneratedFile lists)
    - parser.py           (maps raw LLM JSON → CoderAgentOutput)
    - agents.py route     (builds CoderAgentInput, reads CoderAgentOutput)

Author: Coder Agent (Auto-Forge MAS)
Version: 1.0.0
"""

from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Supporting value models
# ---------------------------------------------------------------------------

class GeneratedFile(BaseModel):
    """
    Represents a single file that the Coder Agent touched during a run.

    Change types:
        new       — file did not exist in the previous project snapshot.
        updated   — file existed and was modified to support the new feature.
        unchanged — file existed and was intentionally left untouched.

    Every file must include a purpose and description so human reviewers
    can understand what changed and why without reading the full source.
    """

    file_path: str = Field(
        ...,
        description="Relative path from the project root. Example: backend/routes/auth.js",
        example="backend/routes/auth.js"
    )
    content: str = Field(
        ...,
        description="Full file content including header comments."
    )
    change_type: Literal["new", "updated", "unchanged"] = Field(
        ...,
        description="Whether this file is new, updated, or unchanged."
    )
    purpose: str = Field(
        ...,
        description="One-sentence description of what this file does.",
        example="Defines Express routes for authentication endpoints."
    )
    description: str = Field(
        ...,
        description="Longer explanation of this file's role in the feature.",
        example=(
            "Registers POST /api/auth/login and POST /api/auth/logout routes. "
            "Delegates business logic to AuthService."
        )
    )
    feature_id: str = Field(
        ...,
        description="ID of the feature this file was generated for."
    )
    version: int = Field(
        default=1,
        description="Version of this file. Increments on each revision."
    )


class EnvVarRequirement(BaseModel):
    """
    Declares one environment variable that the generated code requires.

    The Coder Agent extracts these from the SDS and from its own code
    analysis. The env validator uses this list to block generation if
    required variables are not provided.

    Example:
        name        = "MONGO_URI"
        description = "MongoDB connection string"
        example     = "mongodb://localhost:27017/myapp"
        required    = True
    """

    name: str = Field(
        ...,
        description="Environment variable name in UPPER_SNAKE_CASE.",
        example="MONGO_URI"
    )
    description: str = Field(
        ...,
        description="What this variable is used for.",
        example="MongoDB connection string used by Mongoose."
    )
    example_value: str = Field(
        ...,
        description="A safe, non-secret example value for documentation.",
        example="mongodb://localhost:27017/myapp"
    )
    required: bool = Field(
        default=True,
        description="Whether generation must stop if this variable is missing."
    )


class RequirementCodeMapping(BaseModel):
    """
    Maps one requirement ID to the files that implement it.

    This is the requirement-to-code traceability record.

    Example:
        requirement_id   = "FR-001"
        requirement_text = "User can login using email and password"
        file_paths       = ["backend/routes/auth.js", "backend/services/auth.service.js"]
    """

    requirement_id: str = Field(
        ...,
        description="Requirement ID from the SRS. Example: FR-001",
        example="FR-001"
    )
    requirement_text: str = Field(
        ...,
        description="Short description of the requirement.",
        example="User can login using email and password."
    )
    file_paths: list[str] = Field(
        default_factory=list,
        description="List of file paths that implement this requirement.",
        example=["backend/routes/auth.js", "backend/services/auth.service.js"]
    )


class ArtifactMetadataEntry(BaseModel):
    """
    Metadata block embedded in each Coder Agent artifact.

    Used by human reviewers and downstream agents (e.g. Deployment Agent)
    to understand the provenance of a generated file.
    """

    agent: str = Field(default="coder_agent", description="Name of the agent that created this.")
    feature_id: str = Field(..., description="Feature this artifact belongs to.")
    feature_name: str = Field(..., description="Human-readable feature name.")
    project_id: str = Field(..., description="Project this artifact belongs to.")
    project_name: str = Field(..., description="Human-readable project name.")
    version: int = Field(..., description="Artifact version number.")
    target_stack: str = Field(..., description="Technology stack. Example: MERN")
    generated_files_count: int = Field(..., description="Number of new files generated.")
    updated_files_count: int = Field(..., description="Number of existing files updated.")
    unchanged_files_count: int = Field(..., description="Number of files preserved untouched.")


# ---------------------------------------------------------------------------
# Primary agent input/output models
# ---------------------------------------------------------------------------

class CoderAgentInput(BaseModel):
    """
    Full context required to run the Coder Agent for one feature.

    The API route assembles this model from:
    - Project and feature metadata from the in-memory store
    - Approved artifact content read from disk via artifact_service
    - Previous project snapshot (if this is iteration 2+)
    - Human revision comment (if this is a revision run)
    - Environment variables declared in the request body

    Fields:
        project_id               — Identifies the project in the store.
        project_name             — Used for logging and artifact metadata.
        feature_id               — Identifies the feature being developed.
        feature_name             — Used in prompts and file headers.
        project_type             — E-commerce, LMS, CRM, etc.
        target_stack             — MERN, FastAPI+React, Django, etc.

        approved_srs_markdown    — Approved SRS content from Requirement Agent.
        approved_enhanced_srs_markdown — Approved Enhanced SRS from Domain Agent.
        approved_sds_markdown    — Approved SDS from Architecture Agent.
        approved_ui_design_html  — Approved UI design from UI/UX Agent (optional).

        previous_project_snapshot — List of GeneratedFile from the last code artifact.
                                    Empty for the first feature iteration.
        previous_feature_names    — Names of features already implemented.
                                    Used to build context and avoid re-generating them.

        env_vars_provided        — Dict of env var name → value provided by the human.
                                   Used by the env validator before generation starts.

        coding_standards         — Optional extra coding standards for this run.
        human_comment            — Optional human revision comment.
    """

    # Project context
    project_id: str
    project_name: str
    project_type: str
    target_stack: str

    # Feature context
    feature_id: str
    feature_name: str

    # Approved artifact content (loaded from disk by context_builder)
    approved_srs_markdown: str = Field(
        ...,
        description="Approved SRS Markdown content from Requirement Agent."
    )
    approved_enhanced_srs_markdown: str = Field(
        ...,
        description="Approved Enhanced SRS Markdown content from Domain Agent."
    )
    approved_sds_markdown: str = Field(
        ...,
        description="Approved SDS Markdown content from Architecture Agent."
    )
    approved_ui_design_html: str | None = Field(
        default=None,
        description=(
            "Approved UI design HTML from UI/UX Agent. "
            "Optional — UI/UX Agent may not have run yet."
        )
    )

    # Iterative development context
    previous_project_snapshot: list[GeneratedFile] = Field(
        default_factory=list,
        description=(
            "Files generated in previous iterations. "
            "Empty list means this is the first feature. "
            "The agent uses this to classify new vs updated files."
        )
    )
    previous_feature_names: list[str] = Field(
        default_factory=list,
        description="Names of features already implemented in previous iterations."
    )

    # Environment variables
    env_vars_provided: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Environment variable values provided by the human. "
            "Keys are variable names (e.g. MONGO_URI). "
            "Values are the actual values or placeholder strings. "
            "These are validated before generation starts."
        )
    )

    # Optional overrides
    coding_standards: str | None = Field(
        default=None,
        description="Additional coding standards to include in the generation prompt."
    )
    human_comment: str | None = Field(
        default=None,
        description=(
            "Optional human revision comment. "
            "If provided, the agent applies this feedback to the previous output."
        )
    )


class CoderAgentOutput(BaseModel):
    """
    Full structured output returned by the Coder Agent.

    The API route reads this model and saves each section as a separate
    versioned artifact via artifact_service.

    Fields:
        file_tree                — Nested dict representing the project structure.
        generated_files          — New files created for this feature.
        updated_files            — Existing files modified to support this feature.
        unchanged_files          — Existing files preserved without changes.
        env_vars_required        — All env vars this feature's code depends on.
        run_commands             — Commands to install deps, run migrations, start the app.
        integration_notes        — Notes for the human about integrating this feature.
        requirement_mapping      — Traceability from requirements to files.
        artifact_metadata        — Metadata block for human review.
        setup_instructions_markdown — Human-readable setup guide in Markdown.
        merge_report_markdown    — Summary of what was added, changed, and preserved.
    """

    file_tree: dict = Field(
        ...,
        description=(
            "Nested dictionary representing the full project file structure. "
            "Example: {\"backend\": {\"routes\": {\"auth.js\": None}}}"
        )
    )
    generated_files: list[GeneratedFile] = Field(
        default_factory=list,
        description="New files created for this feature."
    )
    updated_files: list[GeneratedFile] = Field(
        default_factory=list,
        description="Existing files modified to support this feature."
    )
    unchanged_files: list[GeneratedFile] = Field(
        default_factory=list,
        description="Existing files preserved without any modification."
    )
    env_vars_required: list[EnvVarRequirement] = Field(
        default_factory=list,
        description="All environment variables this feature's code depends on."
    )
    run_commands: list[str] = Field(
        default_factory=list,
        description="Shell commands to install dependencies and run the project.",
        example=["npm install", "npm run dev"]
    )
    integration_notes: list[str] = Field(
        default_factory=list,
        description="Notes for the human about integrating this feature into the project.",
        example=["Add MONGO_URI to your .env file before running the backend."]
    )
    requirement_mapping: list[RequirementCodeMapping] = Field(
        default_factory=list,
        description="Traceability mapping from requirement IDs to implementing files."
    )
    artifact_metadata: ArtifactMetadataEntry = Field(
        ...,
        description="Metadata block for this artifact generation run."
    )
    setup_instructions_markdown: str = Field(
        ...,
        description="Human-readable Markdown guide for setting up and running this feature."
    )
    merge_report_markdown: str = Field(
        ...,
        description=(
            "Markdown summary of the merge operation: "
            "what was added, what was updated, and what was preserved."
        )
    )