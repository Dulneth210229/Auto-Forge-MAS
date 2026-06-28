"""
Coder Agent environment variable validator.

Purpose:
    Validate that all required environment variables are provided before
    the Coder Agent begins code generation.

Architecture fit:
    - Called by agent.py BEFORE building the prompt or calling the LLM.
    - Parses SDS JSON to extract any declared env var requirements.
    - Cross-references against the env_vars_provided dict on CoderAgentInput.
    - Raises MissingEnvVarsError (a structured custom exception) on failure.

Why halt before generation?
    Generated code that references undefined env vars is unusable.
    Surfacing this as a pre-generation gate prevents wasted LLM calls and
    gives the human a clear, actionable error message.

Author: Coder Agent (Auto-Forge MAS)
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("coder_agent.env_validator")

# ---------------------------------------------------------------------------
# Known env var patterns extracted from common SDS structures.
# These are checked in addition to anything explicitly declared in the SDS.
# ---------------------------------------------------------------------------
_COMMON_REQUIRED_VAR_KEYWORDS = [
    "mongo_uri",
    "database_url",
    "db_url",
    "jwt_secret",
    "secret_key",
    "api_key",
    "oauth_secret",
    "redis_url",
    "smtp_password",
    "stripe_secret",
]


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class MissingEnvVarsError(Exception):
    """
    Raised when required environment variables are not provided.

    Carries the full list of missing variable names and descriptions so
    the API route can return a structured 400 response.
    """

    def __init__(self, missing_vars: list[dict[str, str]]) -> None:
        self.missing_vars = missing_vars
        names = ", ".join(v["name"] for v in missing_vars)
        super().__init__(
            f"Code generation halted: missing required environment variables: {names}"
        )


# ---------------------------------------------------------------------------
# EnvVarValidator
# ---------------------------------------------------------------------------

@dataclass
class EnvVarValidator:
    """
    Validates required environment variables for the Coder Agent.

    The validator has two sources of required variables:
    1. Variables explicitly declared in the SDS JSON under any of:
       - env_vars, environment_variables, required_env_vars, config
    2. Variables auto-detected by keyword matching against the SDS content.

    The validation strategy is intentionally permissive for MVP:
    if the human provides a var name in env_vars_provided (even with an
    empty string value), it is considered "declared". This allows the
    human to acknowledge a variable without providing a real value during
    development.
    """

    # Optional list of required var names injected externally (for testing)
    required_override: list[str] = field(default_factory=list)

    def extract_required_vars_from_sds(
        self,
        sds_json: dict[str, Any]
    ) -> list[dict[str, str]]:
        """
        Parse the SDS JSON to extract declared environment variable requirements.

        The SDS JSON may declare env vars under various keys depending on how
        the Architecture Agent formatted the output. This method tries all
        common key patterns.

        Args:
            sds_json: The parsed SDS JSON dict from the Architecture Agent artifact.

        Returns:
            List of dicts with keys: name, description, required.
        """
        found: list[dict[str, str]] = []
        seen_names: set[str] = set()

        # Common top-level keys the Architecture Agent may use
        candidate_keys = [
            "env_vars",
            "environment_variables",
            "required_env_vars",
            "configuration",
            "config",
            "environment",
        ]

        for key in candidate_keys:
            value = sds_json.get(key)

            if not value:
                continue

            if isinstance(value, list):
                for item in value:
                    self._extract_var_from_item(item, found, seen_names)

            elif isinstance(value, dict):
                for var_name, var_meta in value.items():
                    if var_name.upper() not in seen_names:
                        seen_names.add(var_name.upper())
                        if isinstance(var_meta, dict):
                            found.append({
                                "name": var_name.upper(),
                                "description": var_meta.get("description", ""),
                                "required": str(var_meta.get("required", True)),
                            })
                        else:
                            found.append({
                                "name": var_name.upper(),
                                "description": str(var_meta),
                                "required": "true",
                            })

        # Auto-detect by scanning the full SDS JSON text for known keywords
        sds_text = str(sds_json).upper()
        for keyword in _COMMON_REQUIRED_VAR_KEYWORDS:
            var_name = keyword.upper()
            if var_name in sds_text and var_name not in seen_names:
                seen_names.add(var_name)
                found.append({
                    "name": var_name,
                    "description": f"Auto-detected from SDS: {var_name}",
                    "required": "true",
                })

        logger.info(
            "[EnvVarValidator] Extracted %d required env vars from SDS.", len(found)
        )

        return found

    def _extract_var_from_item(
        self,
        item: Any,
        found: list[dict[str, str]],
        seen_names: set[str]
    ) -> None:
        """
        Parse a single item from an env vars list in the SDS JSON.

        Handles multiple formats:
            - {"name": "MONGO_URI", "description": "...", "required": true}
            - {"key": "MONGO_URI", "value": "..."}
            - "MONGO_URI"
        """
        if isinstance(item, dict):
            name = (
                item.get("name")
                or item.get("key")
                or item.get("variable")
                or item.get("var")
            )
            if name and isinstance(name, str):
                name = name.upper().strip()
                if name not in seen_names:
                    seen_names.add(name)
                    found.append({
                        "name": name,
                        "description": item.get("description", item.get("value", "")),
                        "required": str(item.get("required", True)),
                    })

        elif isinstance(item, str) and item.strip():
            name = item.upper().strip()
            if name not in seen_names:
                seen_names.add(name)
                found.append({
                    "name": name,
                    "description": f"Required: {name}",
                    "required": "true",
                })

    def validate(
        self,
        required_vars: list[dict[str, str]],
        provided_vars: dict[str, str]
    ) -> None:
        """
        Check that all required environment variables have been provided.

        A variable is considered "provided" if its name (case-insensitive)
        exists as a key in provided_vars.

        Args:
            required_vars:  List of required var dicts with at least "name" and "required".
            provided_vars:  Dict of var name → value provided by the human in the request.

        Raises:
            MissingEnvVarsError: If any required variables are absent from provided_vars.
        """
        provided_upper = {k.upper() for k in provided_vars.keys()}

        missing: list[dict[str, str]] = []

        for var in required_vars:
            is_required = str(var.get("required", "true")).lower() not in ("false", "0", "no")
            if not is_required:
                continue

            name = var.get("name", "").upper()
            if not name:
                continue

            if name not in provided_upper:
                missing.append({
                    "name": name,
                    "description": var.get("description", ""),
                })
                logger.warning(
                    "[EnvVarValidator] Missing required env var: %s", name
                )

        if missing:
            logger.error(
                "[EnvVarValidator] Generation halted. Missing %d env vars: %s",
                len(missing),
                [v["name"] for v in missing]
            )
            raise MissingEnvVarsError(missing_vars=missing)

        logger.info(
            "[EnvVarValidator] All %d required env vars are provided.",
            len(required_vars)
        )

    def validate_from_sds(
        self,
        sds_json: dict[str, Any],
        provided_vars: dict[str, str]
    ) -> list[dict[str, str]]:
        """
        Convenience method: extract required vars from SDS JSON then validate.

        Args:
            sds_json:       Parsed SDS JSON from the Architecture Agent.
            provided_vars:  Env vars provided by the human in the request.

        Returns:
            The list of extracted required vars (useful for logging/debugging).

        Raises:
            MissingEnvVarsError: If any required variables are missing.
        """
        required_vars = self.extract_required_vars_from_sds(sds_json)
        self.validate(required_vars, provided_vars)
        return required_vars


# Module-level singleton
env_validator = EnvVarValidator()
