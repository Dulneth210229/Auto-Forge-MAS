"""
Coder Agent API schemas.

Purpose:
    Define the HTTP request and response shapes for the /coder/run endpoint.

Architecture fit:
    - CoderAgentRunRequest is the FastAPI request body for POST /features/{id}/agents/coder/run.
    - The API route (agents.py) reads this model and maps it to CoderAgentInput.
    - CoderAgentRunResponse extends AgentRunResponse with Coder-specific fields.

Why a separate schema file?
    The Coder Agent's HTTP API needs richer input than AgentRunRequest:
    - env_vars: The human must declare the env vars the generated code depends on.
    - skip_uiux: The UI/UX Agent may not have run yet; this flag allows skipping it.
    - coding_standards: Optional per-run coding standards override.

Author: Coder Agent (Auto-Forge MAS)
Version: 1.0.0
"""

from pydantic import BaseModel, Field


class CoderAgentRunRequest(BaseModel):
    """
    Request body for POST /features/{feature_id}/agents/coder/run.

    Fields:
        human_comment:     Optional revision comment from the human reviewer.
                           If provided, the agent applies the feedback to the
                           previous output rather than generating from scratch.

        env_vars:          Dict of environment variable name → value.
                           The Coder Agent validates that all required vars
                           (extracted from the SDS) are present here before
                           beginning code generation.

                           Keys are variable names: MONGO_URI, JWT_SECRET, etc.
                           Values can be real values or placeholder strings during dev.

                           Example:
                               {
                                 "MONGO_URI": "mongodb://localhost:27017/myapp",
                                 "JWT_SECRET": "dev-secret-key-change-in-prod"
                               }

        skip_uiux:         If True, the agent skips the UI/UX artifact approval gate.
                           This allows running the Coder Agent before the UI/UX Agent
                           has been implemented or run.
                           Default: True (UI/UX Agent is not yet implemented).

        coding_standards:  Optional additional coding standards to inject into the
                           generation prompt. Useful for enforcing team-specific rules
                           on a per-run basis.
                           Example: "Use async/await everywhere. No callbacks."
    """

    human_comment: str | None = Field(
        default=None,
        example="Add input validation for the email field.",
        description=(
            "Optional revision comment. If provided, the agent applies this "
            "feedback to the previous code output."
        )
    )

    env_vars: dict[str, str] = Field(
        default_factory=dict,
        example={
            "MONGO_URI": "mongodb://localhost:27017/myapp",
            "JWT_SECRET": "dev-secret-key-change-in-prod"
        },
        description=(
            "Environment variable values declared by the human. "
            "The Coder Agent validates these against the SDS requirements "
            "before beginning code generation. "
            "Missing required variables will halt generation with a 400 error."
        )
    )

    skip_uiux: bool = Field(
        default=True,
        description=(
            "If True, skip the UI/UX artifact approval gate. "
            "Set to False once the UI/UX Agent is implemented and has run."
        )
    )

    coding_standards: str | None = Field(
        default=None,
        example="Use async/await everywhere. No callbacks. Use TypeScript strict mode.",
        description=(
            "Additional coding standards to inject into the generation prompt. "
            "These are appended to the default standards defined in the system prompt."
        )
    )


class CoderAgentMissingEnvVarsResponse(BaseModel):
    """
    Response returned when required environment variables are missing.

    Returned as HTTP 400 so the human knows exactly which variables to provide
    before retrying the /coder/run call.

    Fields:
        detail:        Human-readable error summary.
        missing_vars:  List of missing variable dicts with name and description.
    """

    detail: str = Field(
        ...,
        example="Code generation halted: missing required environment variables.",
        description="Human-readable error summary."
    )
    missing_vars: list[dict[str, str]] = Field(
        default_factory=list,
        example=[
            {
                "name": "MONGO_URI",
                "description": "MongoDB connection string used by Mongoose."
            }
        ],
        description="List of missing required environment variables."
    )
