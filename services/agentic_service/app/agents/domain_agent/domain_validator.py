"""
Domain Agent Enhancement Validator.

Purpose:
Validate that the Domain Agent's enhanced SRS + domain improvements summary
are internally consistent, and -- critically -- that every claimed
enrichment is actually backed by retrieved domain knowledge rather than
LLM-invented content. That last check is what makes "Domain Agent is a RAG
system" an enforced fact rather than a marketing claim.

This validator is feature-independent. It does not contain e-commerce,
LMS, or any other domain-specific logic.
"""

from __future__ import annotations

from typing import Any

SECTION_KEYS = [
    "functional_requirements",
    "non_functional_requirements",
    "acceptance_criteria",
    "validation_rules",
    "user_stories",
]


class DomainEnhancementValidationError(Exception):
    """
    Raised when the generated enhanced SRS / domain improvements are
    incomplete, inconsistent, or make an enrichment claim unsupported by
    retrieved domain knowledge.
    """


class DomainEnhancementValidator:
    """
    Validates one Domain Agent generation result against the raw SRS it
    was based on and the domain knowledge chunks that were retrieved for it.
    """

    def validate(
        self,
        srs_json: dict[str, Any],
        enhanced_srs_json: dict[str, Any],
        domain_improvements_json: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
    ) -> None:
        """
        Raises DomainEnhancementValidationError if any check fails.
        """

        errors: list[str] = []

        errors.extend(self._validate_no_dropped_ids(srs_json, enhanced_srs_json))
        errors.extend(self._validate_new_id_namespace(srs_json, enhanced_srs_json))
        errors.extend(self._validate_citation_integrity(enhanced_srs_json, domain_improvements_json, retrieved_chunks))
        errors.extend(self._validate_honesty_with_empty_retrieval(domain_improvements_json, retrieved_chunks))
        errors.extend(self._validate_improvements_srs_consistency(srs_json, enhanced_srs_json, domain_improvements_json))

        if errors:
            raise DomainEnhancementValidationError("; ".join(errors))

    def _validate_no_dropped_ids(self, srs_json: dict[str, Any], enhanced_srs_json: dict[str, Any]) -> list[str]:
        errors = []

        for section_key in SECTION_KEYS:
            original_ids = self._collect_ids(srs_json.get(section_key, []))
            enhanced_ids = self._collect_ids(enhanced_srs_json.get(section_key, []))

            missing = [item_id for item_id in original_ids if item_id not in enhanced_ids]

            if missing:
                errors.append(f"Enhanced SRS {section_key} dropped original IDs: {missing}")

        return errors

    def _validate_new_id_namespace(self, srs_json: dict[str, Any], enhanced_srs_json: dict[str, Any]) -> list[str]:
        errors = []

        for section_key in SECTION_KEYS:
            original_ids = set(self._collect_ids(srs_json.get(section_key, [])))
            enhanced_ids = self._collect_ids(enhanced_srs_json.get(section_key, []))

            new_ids = [item_id for item_id in enhanced_ids if item_id not in original_ids]

            for new_id in new_ids:
                if "-DOM-" not in new_id:
                    errors.append(
                        f"Enhanced SRS {section_key} has a new ID '{new_id}' that does not "
                        f"follow the required '-DOM-' namespace (e.g. FR-DOM-001)."
                    )

        return errors

    def _validate_citation_integrity(
        self,
        enhanced_srs_json: dict[str, Any],
        domain_improvements_json: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
    ) -> list[str]:
        errors = []
        retrieved_sources = {chunk.get("source_document") for chunk in retrieved_chunks}

        for section_key in SECTION_KEYS:
            for item in enhanced_srs_json.get(section_key, []):
                if not isinstance(item, dict):
                    continue

                is_flagged = item.get("origin") == "domain_agent" or item.get("modified_by_domain_agent") is True

                if not is_flagged:
                    continue

                citation = item.get("domain_citation") or {}
                source_document = citation.get("source_document")

                if not source_document:
                    errors.append(
                        f"Enhanced SRS {section_key} item '{item.get('id')}' is flagged as "
                        f"domain-enriched but has no domain_citation.source_document."
                    )
                elif source_document not in retrieved_sources:
                    errors.append(
                        f"Enhanced SRS {section_key} item '{item.get('id')}' cites source "
                        f"document '{source_document}' which was not among the retrieved chunks."
                    )

        for addition in domain_improvements_json.get("additions", []):
            errors.extend(self._validate_one_citation(addition, retrieved_sources, "addition", addition.get("new_id")))

        for modification in domain_improvements_json.get("modifications", []):
            errors.extend(self._validate_one_citation(modification, retrieved_sources, "modification", modification.get("id")))

        return errors

    def _validate_one_citation(
        self,
        record: dict[str, Any],
        retrieved_sources: set[str],
        kind: str,
        record_id: Any,
    ) -> list[str]:
        citation = record.get("domain_citation") or {}
        source_document = citation.get("source_document")

        if not source_document:
            return [f"domain_improvements_json {kind} '{record_id}' has no domain_citation.source_document."]

        if source_document not in retrieved_sources:
            return [
                f"domain_improvements_json {kind} '{record_id}' cites source document "
                f"'{source_document}' which was not among the retrieved chunks."
            ]

        return []

    def _validate_honesty_with_empty_retrieval(
        self,
        domain_improvements_json: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
    ) -> list[str]:
        if retrieved_chunks:
            return []

        additions = domain_improvements_json.get("additions", [])
        modifications = domain_improvements_json.get("modifications", [])

        if additions or modifications:
            return [
                "No domain knowledge chunks were retrieved for this feature, but "
                "domain_improvements_json claims additions/modifications. Enrichment must "
                "never be claimed without real retrieved domain knowledge behind it."
            ]

        return []

    def _validate_improvements_srs_consistency(
        self,
        srs_json: dict[str, Any],
        enhanced_srs_json: dict[str, Any],
        domain_improvements_json: dict[str, Any],
    ) -> list[str]:
        errors = []

        for addition in domain_improvements_json.get("additions", []):
            target_section = addition.get("target_section")
            new_id = addition.get("new_id")

            enhanced_ids = self._collect_ids(enhanced_srs_json.get(target_section, []))

            if new_id not in enhanced_ids:
                errors.append(
                    f"domain_improvements_json addition '{new_id}' does not exist in "
                    f"enhanced_srs_json.{target_section}."
                )

        for modification in domain_improvements_json.get("modifications", []):
            target_section = modification.get("target_section")
            item_id = modification.get("id")

            original_item = self._find_item_by_id(srs_json.get(target_section, []), item_id)
            enhanced_item = self._find_item_by_id(enhanced_srs_json.get(target_section, []), item_id)

            if enhanced_item is None:
                errors.append(
                    f"domain_improvements_json modification '{item_id}' does not exist in "
                    f"enhanced_srs_json.{target_section}."
                )
                continue

            if original_item is None:
                errors.append(
                    f"domain_improvements_json modification '{item_id}' does not match any "
                    f"original item in srs_json.{target_section}."
                )
                continue

            claimed_original = modification.get("original_description")
            actual_original = original_item.get("description")

            if claimed_original != actual_original:
                errors.append(
                    f"domain_improvements_json modification '{item_id}' original_description "
                    f"does not match the actual original SRS text."
                )

        return errors

    def _collect_ids(self, items: list[Any]) -> list[str]:
        ids = []

        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))

        return ids

    def _find_item_by_id(self, items: list[Any], item_id: Any) -> dict[str, Any] | None:
        for item in items:
            if isinstance(item, dict) and item.get("id") == item_id:
                return item

        return None
