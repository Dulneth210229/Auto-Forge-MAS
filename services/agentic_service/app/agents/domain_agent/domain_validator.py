"""
Domain Agent Enhancement Validator.

Purpose:
Validate the Domain Agent's PROPOSED enrichment plan (a small list of
additions/modifications, not a full SRS) before it is merged into the SRS by
deterministic Python code. Critically, this is where "Domain Agent is a RAG
system" becomes an enforced fact rather than a marketing claim: every
addition/modification must cite domain knowledge that was actually
retrieved, and if nothing was retrieved, no enrichment may be claimed.

Why plan-level (not merged-output-level) validation:
The final enhanced_srs_json/domain_improvements_json are built by
deterministic Python (_apply_enrichment_plan in agent.py) from a validated
plan, so their internal consistency (no dropped IDs, correct -DOM- numbering,
consistent original_description) is guaranteed by construction -- the LLM
never retypes the SRS or invents IDs, so those classes of error can no
longer happen. Validating the LLM's small proposed plan -- before merge --
is both cheaper and catches problems (bad target_section, a modification id
that doesn't exist, fabricated citations) at the one point they can actually
originate: the LLM.

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
    Raised when a proposed enrichment plan is malformed, references a
    non-existent item, or makes an enrichment claim unsupported by
    retrieved domain knowledge.
    """


class DomainEnhancementValidator:
    """
    Validates one Domain Agent enrichment plan against the SRS (or, for a
    revision, the current enhanced SRS) it will be merged into, and the
    domain knowledge chunks that were retrieved for it.
    """

    def validate_plan(
        self,
        base_srs_json: dict[str, Any],
        plan: dict[str, Any],
        retrieved_chunks: list[dict[str, Any]],
    ) -> None:
        """
        Raises DomainEnhancementValidationError if any check fails.
        """

        additions = plan.get("additions", [])
        modifications = plan.get("modifications", [])

        if not isinstance(additions, list) or not isinstance(modifications, list):
            raise DomainEnhancementValidationError(
                "Enrichment plan 'additions' and 'modifications' must both be lists."
            )

        errors: list[str] = []

        errors.extend(self._validate_additions(additions))
        errors.extend(self._validate_modifications(base_srs_json, modifications))
        errors.extend(self._validate_citation_integrity(additions, modifications, retrieved_chunks))
        errors.extend(self._validate_honesty_with_empty_retrieval(additions, modifications, retrieved_chunks))

        if errors:
            raise DomainEnhancementValidationError("; ".join(errors))

    def _validate_additions(self, additions: list[Any]) -> list[str]:
        errors = []

        for index, addition in enumerate(additions):
            if not isinstance(addition, dict):
                errors.append(f"additions[{index}] must be an object.")
                continue

            target_section = addition.get("target_section")

            if target_section not in SECTION_KEYS:
                errors.append(
                    f"additions[{index}] has invalid target_section '{target_section}'. "
                    f"Must be one of: {SECTION_KEYS}."
                )

            if not str(addition.get("description", "")).strip():
                errors.append(f"additions[{index}] is missing a non-empty description.")

        return errors

    def _validate_modifications(self, base_srs_json: dict[str, Any], modifications: list[Any]) -> list[str]:
        errors = []

        for index, modification in enumerate(modifications):
            if not isinstance(modification, dict):
                errors.append(f"modifications[{index}] must be an object.")
                continue

            target_section = modification.get("target_section")

            if target_section not in SECTION_KEYS:
                errors.append(
                    f"modifications[{index}] has invalid target_section '{target_section}'. "
                    f"Must be one of: {SECTION_KEYS}."
                )
                continue

            item_id = modification.get("id")
            existing_ids = self._collect_ids(base_srs_json.get(target_section, []))

            if not item_id or item_id not in existing_ids:
                errors.append(
                    f"modifications[{index}] references id '{item_id}' which does not exist "
                    f"in {target_section}."
                )

            if not str(modification.get("enhanced_description", "")).strip():
                errors.append(f"modifications[{index}] is missing a non-empty enhanced_description.")

        return errors

    def _validate_citation_integrity(
        self,
        additions: list[Any],
        modifications: list[Any],
        retrieved_chunks: list[dict[str, Any]],
    ) -> list[str]:
        errors = []
        retrieved_sources = {chunk.get("source_document") for chunk in retrieved_chunks}

        for kind, records in (("addition", additions), ("modification", modifications)):
            for index, record in enumerate(records):
                if not isinstance(record, dict):
                    continue

                citation = record.get("domain_citation") or {}
                source_document = citation.get("source_document")

                if not source_document:
                    errors.append(f"{kind}s[{index}] has no domain_citation.source_document.")
                elif source_document not in retrieved_sources:
                    errors.append(
                        f"{kind}s[{index}] cites source document '{source_document}' which was "
                        f"not among the retrieved chunks."
                    )

        return errors

    def _validate_honesty_with_empty_retrieval(
        self,
        additions: list[Any],
        modifications: list[Any],
        retrieved_chunks: list[dict[str, Any]],
    ) -> list[str]:
        if retrieved_chunks:
            return []

        if additions or modifications:
            return [
                "No domain knowledge chunks were retrieved for this feature, but the plan "
                "proposes additions/modifications. Enrichment must never be claimed without "
                "real retrieved domain knowledge behind it."
            ]

        return []

    def _collect_ids(self, items: list[Any]) -> list[str]:
        ids = []

        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))

        return ids
