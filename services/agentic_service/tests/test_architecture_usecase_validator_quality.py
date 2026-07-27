"""
Unit tests for UseCaseQualityValidator's new quality checks added by the
Use Case Diagram rewrite (app/agents/architecture_agent/usecase_validator.py):
_validate_use_case_name_quality and _validate_use_case_fragmentation.
No LLM involved.

Sibling to tests/test_architecture_usecase_validator.py, which owns the
out-of-scope regression fixtures and is left untouched. These fixtures are
the real, confirmed garbled/fragmented examples recorded in the approved
rewrite plan, plus the legitimate names that must NOT be flagged.

Note: an earlier iteration of this rewrite also added a "main use case name
just restates the feature name" check. It was removed after a real
regression: M5's fallback path deliberately names the main use case from
feature_name alone (e.g. "Task Comments"), so for any multi-word feature
name that check made the deterministic last-resort fallback -- the one path
that must always succeed -- deterministically fail its own validation. A
literal feature-name match is not actually invalid UML, just not maximally
descriptive, so the check did more harm than good.
"""

from app.agents.architecture_agent.usecase_validator import (
    UseCaseQualityValidator,
    UseCaseValidationError,
)


def _base_usecase_json(use_cases: list[dict], relationships: list[dict]) -> dict:
    return {
        "system_boundary": "Test System",
        "diagram_title": "Test Diagram",
        "actors": [{"id": "ACT-001", "name": "User", "type": "primary"}],
        "use_cases": use_cases,
        "relationships": relationships,
        "notes": [],
    }


class TestGarbledNameDetection:
    def test_real_garbled_fragment_names_are_flagged(self):
        """
        Real confirmed garbled examples from actual .puml artifacts:
        "A Task The Can", "A Comment The Authored", "A Enters A Keyword".
        """
        validator = UseCaseQualityValidator()
        usecase_json = _base_usecase_json(
            use_cases=[
                {"id": "UC-001", "name": "A Task The Can", "category": "main", "related_requirements": ["FR-001"]},
                {"id": "UC-002", "name": "A Comment The Authored", "category": "included", "related_requirements": ["FR-002"]},
            ],
            relationships=[
                {"from": "ACT-001", "to": "UC-001", "type": "association", "related_requirements": []},
                {"from": "UC-001", "to": "UC-002", "type": "include", "related_requirements": ["FR-002"]},
            ],
        )
        srs_json = {"functional_requirements": [{"id": "FR-001"}, {"id": "FR-002"}]}

        try:
            validator.validate(srs_json, {}, {}, usecase_json)
            assert False, "expected UseCaseValidationError for garbled fragment names"
        except UseCaseValidationError as error:
            assert "cut sentence fragment" in str(error)

    def test_generic_but_not_garbled_name_is_not_flagged_by_name_quality_check(self):
        """
        "Do Something" is generic but not a cut sentence fragment -- must
        not be flagged by the fragment-word check (regression: 'do' is a
        generic auxiliary verb, deliberately excluded from FRAGMENT_WORDS).
        """
        validator = UseCaseQualityValidator()
        errors = validator._validate_use_case_name_quality(
            _base_usecase_json(
                use_cases=[{"id": "UC-001", "name": "Do Something", "category": "main", "related_requirements": []}],
                relationships=[],
            )
        )
        assert errors == []


class TestFragmentationDetection:
    def test_real_three_way_validate_fragmentation_is_caught(self):
        """
        Real confirmed CRUD/step over-fragmentation: "Validate Email",
        "Validate Password", "Validate Credentials" as three separate
        included use cases under one login main use case.
        """
        validator = UseCaseQualityValidator()
        usecase_json = _base_usecase_json(
            use_cases=[
                {"id": "UC-001", "name": "Authenticate User", "category": "main", "related_requirements": ["FR-001"]},
                {"id": "UC-002", "name": "Validate Email", "category": "included", "related_requirements": ["FR-002"]},
                {"id": "UC-003", "name": "Validate Password", "category": "included", "related_requirements": ["FR-003"]},
                {"id": "UC-004", "name": "Validate Credentials", "category": "included", "related_requirements": ["FR-004"]},
            ],
            relationships=[
                {"from": "ACT-001", "to": "UC-001", "type": "association", "related_requirements": []},
                {"from": "UC-001", "to": "UC-002", "type": "include", "related_requirements": ["FR-002"]},
                {"from": "UC-001", "to": "UC-003", "type": "include", "related_requirements": ["FR-003"]},
                {"from": "UC-001", "to": "UC-004", "type": "include", "related_requirements": ["FR-004"]},
            ],
        )
        srs_json = {"functional_requirements": [{"id": f"FR-00{i}"} for i in range(1, 5)]}

        try:
            validator.validate(srs_json, {}, {}, usecase_json)
            assert False, "expected UseCaseValidationError for Validate X/Y/Z fragmentation"
        except UseCaseValidationError as error:
            assert "decomposed internal steps" in str(error)
            assert "Validate" in str(error)

    def test_legitimate_single_validate_credentials_does_not_raise(self):
        """
        A single, properly-named "Validate Credentials" (not fragmented
        into parallel sibling steps) under a properly-named main use case
        must pass cleanly.
        """
        validator = UseCaseQualityValidator()
        usecase_json = _base_usecase_json(
            use_cases=[
                {"id": "UC-001", "name": "Authenticate With Credentials", "category": "main", "related_requirements": ["FR-001"]},
                {"id": "UC-002", "name": "Validate Credentials", "category": "included", "related_requirements": ["FR-002"]},
            ],
            relationships=[
                {"from": "ACT-001", "to": "UC-001", "type": "association", "related_requirements": []},
                {"from": "UC-001", "to": "UC-002", "type": "include", "related_requirements": ["FR-002"]},
            ],
        )
        srs_json = {"functional_requirements": [{"id": "FR-001"}, {"id": "FR-002"}]}

        validator.validate(srs_json, {}, {}, usecase_json)

    def test_shared_related_requirements_duplicate_is_caught(self):
        validator = UseCaseQualityValidator()
        usecase_json = _base_usecase_json(
            use_cases=[
                {"id": "UC-001", "name": "Recover Account Access", "category": "main", "related_requirements": ["FR-001"]},
                {"id": "UC-002", "name": "Initiate Forgot Password Process", "category": "extension", "related_requirements": ["FR-005"]},
                {"id": "UC-003", "name": "Initiate Recovery Flow", "category": "extension", "related_requirements": ["FR-005"]},
            ],
            relationships=[
                {"from": "ACT-001", "to": "UC-001", "type": "association", "related_requirements": []},
                {"from": "UC-002", "to": "UC-001", "type": "extend", "related_requirements": ["FR-005"]},
                {"from": "UC-003", "to": "UC-001", "type": "extend", "related_requirements": ["FR-005"]},
            ],
        )
        srs_json = {"functional_requirements": [{"id": "FR-001"}, {"id": "FR-005"}]}

        try:
            validator.validate(srs_json, {}, {}, usecase_json)
            assert False, "expected UseCaseValidationError for same-requirement-id duplicates"
        except UseCaseValidationError as error:
            assert "cite the exact same requirements" in str(error)
