"""
Unit tests for CodePlanValidator -- hand-crafted inputs, no LLM involved.

Mirrors test_uiux_metadata_validator.py's structure: confirm the validator
actually rejects incomplete endpoint/entity/requirement coverage rather than
silently passing.
"""

import pytest

from app.agents.coder_agent.plan_validator import (
    CodePlanValidationError,
    CodePlanValidator,
)

SRS = {
    "functional_requirements": [
        {"id": "FR-001", "description": "Users can log in."},
        {"id": "FR-002", "description": "System validates credentials."},
    ],
}

ARCHITECTURE_PLAN = {
    "design_views": {
        "interface_view": {
            "api_endpoints": [
                {"endpoint": "/api/auth/login", "method": "POST"},
                {"endpoint": "/api/auth/forgot-password", "method": "GET"},
            ],
        },
        "data_view": {
            "data_entities": [{"name": "User Credentials"}],
        },
    },
}


def _complete_plan() -> dict:
    return {
        "files": [
            {
                "path": "server/src/routes/auth.routes.js",
                "action": "create",
                "rationale": "Login and forgot-password endpoints.",
                "maps_to": ["/api/auth/login", "/api/auth/forgot-password", "FR-001", "FR-002"],
            },
            {
                "path": "server/src/models/UserCredentials.js",
                "action": "create",
                "rationale": "Persist user credentials.",
                "maps_to": ["User Credentials"],
            },
        ],
        "new_dependencies": [],
        "env_vars_needed": ["JWT_SECRET"],
        "summary": "Implement login.",
    }


@pytest.fixture
def validator():
    return CodePlanValidator()


def test_complete_plan_passes(validator):
    validator.validate(SRS, ARCHITECTURE_PLAN, _complete_plan())  # should not raise


def test_missing_endpoint_coverage_fails(validator):
    plan = _complete_plan()
    plan["files"][0]["maps_to"] = ["/api/auth/login", "FR-001", "FR-002"]  # forgot-password missing

    with pytest.raises(CodePlanValidationError, match="forgot-password"):
        validator.validate(SRS, ARCHITECTURE_PLAN, plan)


def test_missing_entity_coverage_fails(validator):
    plan = _complete_plan()
    plan["files"] = [plan["files"][0]]  # drop the file that maps to User Credentials

    with pytest.raises(CodePlanValidationError, match="User Credentials"):
        validator.validate(SRS, ARCHITECTURE_PLAN, plan)


def test_missing_requirement_coverage_fails(validator):
    plan = _complete_plan()
    plan["files"][0]["maps_to"] = ["/api/auth/login", "/api/auth/forgot-password", "FR-001"]  # FR-002 missing

    with pytest.raises(CodePlanValidationError, match="FR-002"):
        validator.validate(SRS, ARCHITECTURE_PLAN, plan)


def test_empty_files_fails(validator):
    with pytest.raises(CodePlanValidationError, match="non-empty list"):
        validator.validate(SRS, ARCHITECTURE_PLAN, {"files": []})


def test_invalid_action_fails(validator):
    plan = _complete_plan()
    plan["files"][0]["action"] = "rewrite_everything"

    with pytest.raises(CodePlanValidationError, match="invalid action"):
        validator.validate(SRS, ARCHITECTURE_PLAN, plan)


def test_missing_path_fails(validator):
    plan = _complete_plan()
    del plan["files"][0]["path"]

    with pytest.raises(CodePlanValidationError, match="path"):
        validator.validate(SRS, ARCHITECTURE_PLAN, plan)


def test_missing_maps_to_field_fails(validator):
    plan = _complete_plan()
    del plan["files"][0]["maps_to"]

    with pytest.raises(CodePlanValidationError, match="maps_to"):
        validator.validate(SRS, ARCHITECTURE_PLAN, plan)
