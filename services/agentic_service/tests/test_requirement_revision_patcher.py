"""
Tests for the deterministic SRS revision patcher (app/agents/requirement_agent/revision_patcher.py).

This locks in the fix for a real reported bug: asking the LLM to retype the entire SRS for a
revision was unreliable, and a genuine "remove this specific non-functional requirement" comment
was silently dropped. These tests exercise the deterministic apply step in isolation -- no LLM,
no fallback ladder -- since that step is what must now reliably make a requested change actually
happen once the (small, more-reliable) plan names it.
"""

from app.agents.requirement_agent.revision_patcher import apply_revision_operations


def _srs():
    return {
        "functional_requirements": [
            {"id": "FR-001", "description": "Admin can create a task", "priority": "Must Have"},
        ],
        "non_functional_requirements": [
            {"id": "NFR-001", "description": "System should be secure", "category": "Security"},
            {
                "id": "NFR-002",
                "description": "Listing page must load within 2 seconds for up to 10,000 items",
                "category": "Performance",
            },
        ],
        "acceptance_criteria": [
            {"id": "AC-001", "description": "Admin can see a list of tasks."},
        ],
        "user_stories": [
            {"id": "US-001", "role": "Admin", "goal": "manage tasks", "benefit": "stay organized"},
        ],
        "scope": ["Implement task management."],
        "assumptions": [],
    }


def test_remove_id_description_item_by_exact_text():
    srs = _srs()
    operations = [
        {
            "action": "remove",
            "field": "non_functional_requirements",
            "target": "Listing page must load within 2 seconds for up to 10,000 items",
        }
    ]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert len(patched["non_functional_requirements"]) == 1
    assert patched["non_functional_requirements"][0]["id"] == "NFR-001"
    assert not unmatched
    assert len(applied) == 1


def test_remove_id_description_item_by_id():
    srs = _srs()
    operations = [{"action": "remove", "field": "non_functional_requirements", "target": "NFR-002"}]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert len(patched["non_functional_requirements"]) == 1
    assert not unmatched


def test_remove_by_partial_distinctive_substring():
    srs = _srs()
    operations = [{"action": "remove", "field": "non_functional_requirements", "target": "10,000 items"}]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert len(patched["non_functional_requirements"]) == 1
    assert patched["non_functional_requirements"][0]["id"] == "NFR-001"
    assert not unmatched


def test_unmatched_removal_is_reported_not_silently_dropped():
    srs = _srs()
    operations = [{"action": "remove", "field": "non_functional_requirements", "target": "Something not in the SRS"}]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert len(patched["non_functional_requirements"]) == 2
    assert not applied
    assert len(unmatched) == 1
    assert "Something not in the SRS" in unmatched[0]


def test_add_functional_requirement_gets_next_stable_id():
    srs = _srs()
    operations = [
        {"action": "add", "field": "functional_requirements", "value": "Admin can archive a task", "priority": "Should Have"}
    ]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert len(patched["functional_requirements"]) == 2
    assert patched["functional_requirements"][1]["id"] == "FR-002"
    assert patched["functional_requirements"][1]["priority"] == "Should Have"
    assert not unmatched


def test_modify_replaces_description_in_place_keeping_id():
    srs = _srs()
    operations = [
        {"action": "modify", "field": "acceptance_criteria", "target": "AC-001", "value": "Admin can filter the task list by status."}
    ]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert patched["acceptance_criteria"][0]["id"] == "AC-001"
    assert patched["acceptance_criteria"][0]["description"] == "Admin can filter the task list by status."
    assert not unmatched


def test_string_list_field_add_and_remove():
    srs = _srs()
    operations = [
        {"action": "add", "field": "scope", "value": "Support recurring tasks."},
        {"action": "remove", "field": "scope", "target": "Implement task management."},
    ]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert patched["scope"] == ["Support recurring tasks."]
    assert not unmatched


def test_user_story_add():
    srs = _srs()
    operations = [
        {"action": "add", "field": "user_stories", "role": "Guest", "value": "browse public tasks", "benefit": "see what's available"}
    ]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert len(patched["user_stories"]) == 2
    assert patched["user_stories"][1]["id"] == "US-002"
    assert patched["user_stories"][1]["role"] == "Guest"
    assert not unmatched


def test_traceability_is_rebuilt_after_functional_requirement_removal():
    srs = _srs()
    srs["functional_requirements"].append({"id": "FR-002", "description": "Admin can delete a task", "priority": "Must Have"})
    operations = [{"action": "remove", "field": "functional_requirements", "target": "FR-001"}]

    patched, _, _ = apply_revision_operations(srs, operations)

    assert [row["requirement_id"] for row in patched["traceability"]] == ["FR-002"]


def test_malformed_operation_is_skipped_not_raised():
    srs = _srs()
    operations = ["not a dict", {"action": "remove", "field": "unsupported_field", "target": "x"}]

    patched, applied, unmatched = apply_revision_operations(srs, operations)

    assert not applied
    assert len(unmatched) == 2
    # Existing content is untouched by the malformed/unsupported operations.
    assert patched["non_functional_requirements"] == srs["non_functional_requirements"]
