"""
Unit tests for DomainEnhancementValidator.

Pure Python, no embedding/LLM calls. These tests are the enforcement proof
that Domain Agent behaves as a real RAG system: every claimed enrichment
must cite a source among the retrieved chunks, and no enrichment may be
claimed at all when retrieval returned nothing.
"""

import copy

import pytest

from app.agents.domain_agent.domain_validator import (
    DomainEnhancementValidationError,
    DomainEnhancementValidator,
)

SRS_JSON = {
    "functional_requirements": [
        {"id": "FR-001", "description": "Users can log in with email and password."},
    ],
    "non_functional_requirements": [],
    "acceptance_criteria": [
        {"id": "AC-001", "description": "Given valid credentials, the user is logged in."},
    ],
    "validation_rules": [],
    "user_stories": [],
}

RETRIEVED_CHUNKS = [
    {"chunk_id": "auth.txt#0", "source_document": "auth.txt", "text": "Lock the account after 5 failed attempts."},
]


def _valid_enhanced_srs():
    enhanced = copy.deepcopy(SRS_JSON)
    enhanced["functional_requirements"].append({
        "id": "FR-DOM-001",
        "description": "Lock the account after 5 consecutive failed login attempts.",
        "priority": "Should Have",
        "origin": "domain_agent",
        "domain_citation": {"source_document": "auth.txt", "chunk_id": "auth.txt#0"},
    })
    return enhanced


def _valid_improvements():
    return {
        "summary": "Added account lockout requirement.",
        "knowledge_sources_used": [{"source_document": "auth.txt", "chunks_used": 1}],
        "additions": [
            {
                "target_section": "functional_requirements",
                "new_id": "FR-DOM-001",
                "description": "Lock the account after 5 consecutive failed login attempts.",
                "rationale": "Prevent brute-force attacks.",
                "domain_citation": {"source_document": "auth.txt", "chunk_id": "auth.txt#0"},
            }
        ],
        "modifications": [],
        "no_changes_note": None,
    }


def test_valid_enhancement_passes():
    DomainEnhancementValidator().validate(SRS_JSON, _valid_enhanced_srs(), _valid_improvements(), RETRIEVED_CHUNKS)


def test_dropped_original_id_is_rejected():
    enhanced = copy.deepcopy(SRS_JSON)
    enhanced["functional_requirements"] = []  # FR-001 dropped

    with pytest.raises(DomainEnhancementValidationError, match="dropped original IDs"):
        DomainEnhancementValidator().validate(SRS_JSON, enhanced, {"additions": [], "modifications": []}, RETRIEVED_CHUNKS)


def test_new_id_without_dom_namespace_is_rejected():
    enhanced = copy.deepcopy(SRS_JSON)
    enhanced["functional_requirements"].append({
        "id": "FR-002",  # missing the required "-DOM-" segment
        "description": "New requirement.",
        "origin": "domain_agent",
        "domain_citation": {"source_document": "auth.txt", "chunk_id": "auth.txt#0"},
    })

    with pytest.raises(DomainEnhancementValidationError, match="does not follow the required '-DOM-' namespace"):
        DomainEnhancementValidator().validate(SRS_JSON, enhanced, {"additions": [], "modifications": []}, RETRIEVED_CHUNKS)


def test_citation_to_a_source_not_actually_retrieved_is_rejected():
    enhanced = _valid_enhanced_srs()
    enhanced["functional_requirements"][-1]["domain_citation"]["source_document"] = "never_retrieved.txt"

    improvements = _valid_improvements()
    improvements["additions"][0]["domain_citation"]["source_document"] = "never_retrieved.txt"

    with pytest.raises(DomainEnhancementValidationError, match="was not among the retrieved chunks"):
        DomainEnhancementValidator().validate(SRS_JSON, enhanced, improvements, RETRIEVED_CHUNKS)


def test_flagged_item_without_citation_is_rejected():
    enhanced = copy.deepcopy(SRS_JSON)
    enhanced["functional_requirements"].append({
        "id": "FR-DOM-001",
        "description": "New requirement.",
        "origin": "domain_agent",
        # no domain_citation
    })

    with pytest.raises(DomainEnhancementValidationError, match="no domain_citation.source_document"):
        DomainEnhancementValidator().validate(SRS_JSON, enhanced, {"additions": [], "modifications": []}, RETRIEVED_CHUNKS)


def test_honesty_check_rejects_additions_claimed_with_empty_retrieval():
    with pytest.raises(DomainEnhancementValidationError, match="No domain knowledge chunks were retrieved"):
        DomainEnhancementValidator().validate(
            SRS_JSON, _valid_enhanced_srs(), _valid_improvements(), retrieved_chunks=[]
        )


def test_honesty_check_allows_no_changes_with_empty_retrieval():
    empty_improvements = {
        "additions": [],
        "modifications": [],
        "no_changes_note": "No relevant domain knowledge was retrieved for this feature.",
    }

    DomainEnhancementValidator().validate(SRS_JSON, copy.deepcopy(SRS_JSON), empty_improvements, retrieved_chunks=[])


def test_addition_new_id_must_exist_in_enhanced_srs():
    improvements = _valid_improvements()
    improvements["additions"][0]["new_id"] = "FR-DOM-999"  # does not exist in enhanced SRS

    with pytest.raises(DomainEnhancementValidationError, match="does not exist in enhanced_srs_json"):
        DomainEnhancementValidator().validate(SRS_JSON, _valid_enhanced_srs(), improvements, RETRIEVED_CHUNKS)


def test_modification_original_description_must_match_raw_srs():
    enhanced = copy.deepcopy(SRS_JSON)
    enhanced["acceptance_criteria"][0]["description"] = "Enriched wording."
    enhanced["acceptance_criteria"][0]["modified_by_domain_agent"] = True
    enhanced["acceptance_criteria"][0]["domain_citation"] = {"source_document": "auth.txt", "chunk_id": "auth.txt#0"}

    improvements = {
        "additions": [],
        "modifications": [
            {
                "target_section": "acceptance_criteria",
                "id": "AC-001",
                "original_description": "This does not match the real original text.",
                "enhanced_description": "Enriched wording.",
                "rationale": "Domain detail added.",
                "domain_citation": {"source_document": "auth.txt", "chunk_id": "auth.txt#0"},
            }
        ],
    }

    with pytest.raises(DomainEnhancementValidationError, match="does not match the actual original SRS text"):
        DomainEnhancementValidator().validate(SRS_JSON, enhanced, improvements, RETRIEVED_CHUNKS)
