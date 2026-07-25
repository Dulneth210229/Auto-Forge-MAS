"""
Unit tests for DomainAgent's deterministic fallback path.

Pure Python -- exercises _build_fallback_domain_output,
_build_fallback_revise_domain_output, and _finalize_enhanced_srs_metadata
directly, with no LLM/embedding calls. Proves the fallback never fabricates
domain content and always produces validator-passing output.
"""

import copy

from app.agents.domain_agent.agent import DomainAgent

SRS_JSON = {
    "project_id": "proj_1",
    "feature_id": "feature_1",
    "functional_requirements": [{"id": "FR-001", "description": "Users can log in."}],
    "non_functional_requirements": [],
    "acceptance_criteria": [{"id": "AC-001", "description": "Given valid credentials, login succeeds."}],
    "validation_rules": [],
    "user_stories": [],
    "assumptions": [],
    "risks": [],
}


def test_fallback_with_empty_retrieval_preserves_srs_and_explains_why():
    agent = DomainAgent()

    enhanced, improvements = agent._build_fallback_domain_output(SRS_JSON, retrieved_chunks=[], reason="parse failed")

    assert enhanced == SRS_JSON  # content-preserving, no fabricated additions
    assert improvements["additions"] == []
    assert improvements["modifications"] == []
    assert improvements["no_changes_note"] == "No relevant domain knowledge was retrieved for this feature."


def test_fallback_with_nonempty_retrieval_reports_the_failure_reason():
    agent = DomainAgent()
    retrieved_chunks = [{"chunk_id": "auth.txt#0", "source_document": "auth.txt", "text": "..."}]

    _, improvements = agent._build_fallback_domain_output(SRS_JSON, retrieved_chunks, reason="LLM timeout")

    assert "LLM timeout" in improvements["no_changes_note"]
    assert improvements["additions"] == []
    assert improvements["modifications"] == []


def test_finalize_metadata_sets_fallback_flag_and_reason():
    agent = DomainAgent()
    enhanced = copy.deepcopy(SRS_JSON)

    agent._finalize_enhanced_srs_metadata(
        enhanced, srs_version=3, retrieved_chunks=[], fallback_used=True, fallback_reason="boom"
    )

    metadata = enhanced["domain_enrichment_metadata"]
    assert metadata["based_on_srs_version"] == 3
    assert metadata["fallback_used"] is True
    assert metadata["fallback_reason"] == "boom"


def test_finalize_metadata_omits_reason_when_not_fallback():
    agent = DomainAgent()
    enhanced = copy.deepcopy(SRS_JSON)

    agent._finalize_enhanced_srs_metadata(
        enhanced, srs_version=1, retrieved_chunks=[], fallback_used=False, fallback_reason=None
    )

    metadata = enhanced["domain_enrichment_metadata"]
    assert metadata["fallback_used"] is False
    assert "fallback_reason" not in metadata


def test_fallback_output_passes_the_validator():
    agent = DomainAgent()

    enhanced, improvements = agent._build_fallback_domain_output(SRS_JSON, retrieved_chunks=[], reason="parse failed")
    agent._finalize_enhanced_srs_metadata(enhanced, srs_version=1, retrieved_chunks=[], fallback_used=True, fallback_reason="parse failed")

    # Must not raise -- the fallback path must always be validator-clean.
    agent.validator.validate(SRS_JSON, enhanced, improvements, retrieved_chunks=[])


def test_revision_fallback_preserves_existing_enrichment():
    agent = DomainAgent()
    existing_enhanced = copy.deepcopy(SRS_JSON)
    existing_enhanced["functional_requirements"].append({
        "id": "FR-DOM-001",
        "description": "Existing domain addition.",
        "origin": "domain_agent",
        "domain_citation": {"source_document": "auth.txt", "chunk_id": "auth.txt#0"},
    })
    existing_improvements = {
        "additions": [{
            "target_section": "functional_requirements",
            "new_id": "FR-DOM-001",
            "description": "Existing domain addition.",
            "rationale": "Prior run.",
            "domain_citation": {"source_document": "auth.txt", "chunk_id": "auth.txt#0"},
        }],
        "modifications": [],
    }

    enhanced, improvements = agent._build_fallback_revise_domain_output(
        existing_enhanced, existing_improvements, "add mfa", "human_user", "LLM revision failed"
    )

    # Existing FR-DOM-001 addition must survive the fallback untouched.
    assert any(item.get("id") == "FR-DOM-001" for item in enhanced["functional_requirements"])
    assert improvements["additions"] == existing_improvements["additions"]
    assert "add mfa" in improvements["no_changes_note"]
