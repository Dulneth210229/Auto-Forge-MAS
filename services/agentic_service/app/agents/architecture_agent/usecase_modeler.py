"""
Architecture Agent Use Case Modeler.

Purpose:
Build a standard UML Use Case model from approved SRS/SDS data.

Design principle:
This file is feature-independent. It does not hardcode Login, Cart, Payment,
LMS, or any other feature. It uses generic UML rules:
- actors come from external roles/systems
- main use case represents the feature goal
- mandatory supporting behaviour becomes <<include>>
- optional/alternative/error/recovery behaviour becomes <<extend>>
- constraints, NFRs, risks, and architecture decisions stay in the SDS, not as
  visible notes in the use case diagram
"""

from __future__ import annotations

import re
from typing import Any


class ArchitectureUseCaseModeler:
    """
    Builds usecase_analysis_json and final usecase_json.

    The LLM may provide an intermediate usecase_specification_json, but the final
    UML model is normalized here using deterministic, feature-independent rules.
    """

    TECHNICAL_ACTOR_WORDS = [
        "database", "mongodb", "mysql", "postgres", "collection", "table",
        "api", "endpoint", "controller", "server", "backend", "frontend",
        "react", "node", "express", "jwt", "token", "library", "middleware",
        "component", "page", "form", "repository", "schema", "model",
        "service layer",
    ]

    OPTIONAL_WORDS = [
        "optional", "alternative", "recover", "recovery", "forgot", "reset",
        "retry", "re enter", "re-enter", "cancel", "skip", "if", "when",
        "unless", "direct", "redirect", "link", "initiate",
    ]

    ERROR_WORDS = [
        "invalid", "error", "failed", "failure", "fail", "prevent", "denied",
        "unauthorized", "forbidden", "not found", "incorrect", "exception",
        "timeout", "unavailable",
    ]

    INTERNAL_ACTION_VERBS = [
        "validate", "verify", "check", "calculate", "generate", "create", "save",
        "store", "retrieve", "process", "submit", "confirm", "apply", "update",
        "delete", "return",
    ]

    def build(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
        usecase_specification_json: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Build usecase_analysis_json and usecase_json.
        """

        specification = self._normalize_specification(
            srs_json=srs_json,
            sds_json=sds_json,
            specification=usecase_specification_json or {},
        )

        actors = self._build_actors(specification, srs_json, sds_json)

        if specification["use_cases"]:
            # Primary path: the LLM supplied a real use_cases[] list -- trust
            # its naming/categorization directly rather than re-deriving use
            # cases from raw SRS sentences via regex (the confirmed source of
            # garbled/fragmented names).
            main_use_cases, included_use_cases, extension_use_cases = (
                self._build_use_cases_from_specification(specification, srs_json)
            )
        else:
            # Last-resort fallback: no usable specification at all (every
            # generation rung including repair failed). See the fallback
            # naming helpers below for how this stays honest/minimal instead
            # of aggressively fabricating names from raw requirement text.
            main_use_cases = self._build_main_use_cases(specification, srs_json)
            included_use_cases = self._build_included_use_cases(specification, srs_json)
            extension_use_cases = self._build_extension_use_cases(specification, srs_json)

        # Dedup across included+extension together, not each list separately
        # -- a real run surfaced two differently-categorized entries (one
        # included, one extension) that both named the same underlying
        # behaviour (confirmed: both truncated to the identical fallback
        # name "Find Specific Tasks Quickly Using" for a Task Search
        # feature). Per-list dedup alone cannot catch a duplicate that
        # spans a category boundary.
        included_use_cases, extension_use_cases = self._merge_near_duplicates_across_categories(
            included_use_cases, extension_use_cases
        )

        main_use_cases, included_use_cases, extension_use_cases = self._renumber_use_cases(
            main_use_cases=main_use_cases,
            included_use_cases=included_use_cases,
            extension_use_cases=extension_use_cases,
        )

        relationships = self._build_relationships(
            actors=actors,
            main_use_cases=main_use_cases,
            included_use_cases=included_use_cases,
            extension_use_cases=extension_use_cases,
        )

        use_cases: list[dict[str, Any]] = []
        use_cases.extend(main_use_cases)
        use_cases.extend(included_use_cases)
        use_cases.extend(extension_use_cases)

        # Standard project decision: no visual UML notes.
        # NFRs/constraints/risks are documented in the SDS design views.
        notes: list[dict[str, Any]] = []

        usecase_json = {
            "system_boundary": specification["system_boundary"],
            "diagram_title": specification["diagram_title"],
            "actors": actors,
            "use_cases": use_cases,
            "relationships": relationships,
            "notes": notes,
            "standards_notes": [
                "Actors are external roles or external systems outside the system boundary.",
                "Use cases are user-goal behaviours inside the system boundary.",
                "<<include>> is used only for mandatory supporting behaviour.",
                "<<extend>> is used only for optional, alternative, recovery, or exception behaviour.",
                "Constraints, NFRs, risks, and architecture decisions are kept in the SDS, not rendered as UML notes.",
            ],
        }

        usecase_analysis_json = self._build_analysis(
            specification=specification,
            actors=actors,
            main_use_cases=main_use_cases,
            included_use_cases=included_use_cases,
            extension_use_cases=extension_use_cases,
            relationships=relationships,
        )

        return usecase_analysis_json, usecase_json

    # ------------------------------------------------------------------
    # Model building
    # ------------------------------------------------------------------

    def _normalize_specification(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
        specification: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize LLM specification and fill missing boilerplate from SRS/SDS.

        `use_cases` (the current, trusted schema -- see build()) is passed
        through as-is when the LLM supplied one. The legacy
        `primary_use_cases`/`included_behaviours`/`extension_behaviours`/
        `exception_flows` keys are kept only as a defensive secondary read
        (for an older-shaped specification) -- deliberately NOT populated
        with synthesized defaults here anymore, so a genuinely empty
        specification is never silently disguised as "the LLM already
        provided something usable." That synthesis now lives only in the
        deterministic fallback path in build().
        """

        feature_name = self._get_feature_name(srs_json, sds_json)

        use_cases_raw = specification.get("use_cases")
        if not isinstance(use_cases_raw, list):
            use_cases_raw = []

        return {
            "system_boundary": specification.get("system_boundary") or f"{feature_name} Feature",
            "diagram_title": specification.get("diagram_title") or f"{feature_name} Use Case Diagram",
            "actors": specification.get("actors") or specification.get("primary_actors") or srs_json.get("user_roles", []),
            "use_cases": use_cases_raw,
            "primary_use_cases": specification.get("primary_use_cases") or specification.get("main_use_cases") or [],
            "included_behaviours": specification.get("included_behaviours") or specification.get("mandatory_included_behaviours") or [],
            "extension_behaviours": specification.get("extension_behaviours") or specification.get("alternative_flows") or [],
            "exception_flows": specification.get("exception_flows") or [],
        }

    def _build_actors(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build actors from SRS roles and SDS context.
        """

        actor_candidates: list[Any] = []
        actor_candidates.extend(self._as_list(specification.get("actors")))
        actor_candidates.extend(self._as_list(srs_json.get("user_roles")))

        context_view = self._get_design_view(sds_json, "context_view")
        actor_candidates.extend(self._as_list(context_view.get("actors")))
        actor_candidates.extend(self._as_list(context_view.get("external_systems")))

        names: list[str] = []

        for candidate in actor_candidates:
            name = self._extract_name(candidate)
            if not name:
                continue
            if self._is_technical_actor(name):
                continue
            if name.lower() not in [item.lower() for item in names]:
                names.append(self._title_case(name))

        if not names:
            names = ["User"]

        actors = []
        for index, name in enumerate(names, start=1):
            actors.append({
                "id": f"ACT-{index:03d}",
                "name": name,
                "type": "primary" if index == 1 else "secondary",
                "description": f"{name} interacts with the feature to achieve a user goal.",
            })

        return actors

    def _build_use_cases_from_specification(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Build main/included/extension use-case lists directly from the LLM's
        own use_cases[] list -- trusted as-is (only light name cleanup via
        _new_use_case), no regex-based sentence-mining. This is the primary
        path whenever the LLM supplied a real use_cases list;
        _build_main_use_cases/_build_included_use_cases/_build_extension_use_cases
        remain only as the last-resort fallback for a genuinely empty
        specification.
        """

        main: list[dict[str, Any]] = []
        included: list[dict[str, Any]] = []
        extension: list[dict[str, Any]] = []

        for item in specification.get("use_cases", []):
            if not isinstance(item, dict):
                continue

            name = self._extract_name(item)
            if not name:
                continue

            description = self._extract_description(item) or name
            related = self._extract_related_ids(item)
            category = str(item.get("type") or item.get("category") or "included").strip().lower()
            if category not in {"main", "included", "extension"}:
                category = "included"

            use_case = self._new_use_case(name, description, category, related)

            if category == "main":
                main.append(use_case)
            elif category == "extension":
                extension.append(use_case)
            else:
                included.append(use_case)

        # Guarantee exactly one main use case even if the LLM mis-categorized
        # -- promote the first available entry rather than silently
        # producing a diagram with no main goal at all. Update the
        # "category" field itself, not just which list it lives in, so
        # downstream category filters (validator, tests, PlantUML builder)
        # see it consistently.
        if not main and included:
            promoted = included.pop(0)
            promoted["category"] = "main"
            main.append(promoted)
        elif not main and extension:
            promoted = extension.pop(0)
            promoted["category"] = "main"
            main.append(promoted)
        elif not main:
            feature_name = self._get_feature_name(srs_json, {})
            main.append(self._new_use_case(
                feature_name,
                f"Main user goal for the {feature_name} feature.",
                "main",
                self._collect_ids(srs_json.get("functional_requirements", [])),
            ))

        # A feature-level diagram has exactly one main goal -- if the LLM
        # produced more than one "main" entry, keep the first and fold the
        # rest in as included behaviours rather than discarding them.
        if len(main) > 1:
            demoted = main[1:]
            for use_case in demoted:
                use_case["category"] = "included"
            included = demoted + included
            main = main[:1]

        return main, included, extension

    def _build_main_use_cases(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build the main use case (fallback path only -- see
        _build_use_cases_from_specification for the primary, LLM-trusting
        path).

        Named cleanly from feature_name only -- no business-goal regex
        mangling. A feature name (e.g. "Login", "Task Search") is already a
        reasonable, human-authored use case name; synthesizing something
        "better" from a raw business_goal sentence via regex phrase-surgery
        is exactly the failure mode this last-resort path exists to avoid.
        """

        feature_name = self._get_feature_name(srs_json, {})
        primary_items = self._as_list(specification.get("primary_use_cases"))

        if primary_items:
            item = primary_items[0]
            name = self._extract_name(item) or feature_name
            description = self._extract_description(item) or f"Main user goal for the {feature_name} feature."
            related = self._extract_related_ids(item) or self._collect_ids(srs_json.get("functional_requirements", []))
        else:
            name = feature_name
            description = self._get_text(srs_json, "business_goal") or f"Main user goal for the {feature_name} feature."
            related = self._collect_ids(srs_json.get("functional_requirements", []))

        return [{
            "id": "UC-001",
            "name": self._clean_use_case_name(name),
            "description": description,
            "category": "main",
            "related_requirements": related,
        }]

    def _build_included_use_cases(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build included use cases from mandatory behaviours and validation
        rules (fallback path only). Names come from
        _build_fallback_supporting_use_case -- a user-story goal match, or
        one gentle truncation -- no multi-pass regex verb/topic extraction.
        """

        result: list[dict[str, Any]] = []

        for item in self._as_list(specification.get("included_behaviours")):
            description = self._extract_description(item) or self._extract_name(item)
            if not description:
                continue
            related = self._extract_related_ids(item)
            name = self._extract_name(item) or self._build_fallback_supporting_use_case(item, srs_json)
            if name:
                result.append(self._new_use_case(name, description, "included", related))

        for rule in self._as_list(srs_json.get("validation_rules")):
            rule_text = self._extract_description(rule) or self._extract_name(rule)
            rule_id = self._extract_id(rule)
            if not rule_text:
                continue

            name = self._build_fallback_supporting_use_case(rule, srs_json)
            if name:
                result.append(
                    self._new_use_case(
                        name=name,
                        description=rule_text,
                        category="included",
                        related=[rule_id] if rule_id else [],
                    )
                )

        for requirement in self._as_list(srs_json.get("functional_requirements")):
            description = self._extract_description(requirement) or self._extract_name(requirement)
            req_id = self._extract_id(requirement)
            if not description:
                continue

            lowered = self._normalize_words(description)

            # Optional/error/recovery behaviours are handled as extensions.
            if self._has_any(lowered, self.OPTIONAL_WORDS) or self._has_any(lowered, self.ERROR_WORDS):
                continue

            # Only internal mandatory system actions become includes.
            if not self._has_any(lowered, self.INTERNAL_ACTION_VERBS):
                continue

            name = self._build_fallback_supporting_use_case(requirement, srs_json)
            if name:
                result.append(
                    self._new_use_case(
                        name=name,
                        description=description,
                        category="included",
                        related=[req_id] if req_id else [],
                    )
                )

        return result

    def _build_extension_use_cases(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build extension use cases from optional, alternative, recovery, and
        error flows (fallback path only). Names come from
        _build_fallback_supporting_use_case -- a user-story goal match, or
        one gentle truncation -- no multi-pass regex verb/topic extraction.
        """

        result: list[dict[str, Any]] = []

        extension_sources = []
        extension_sources.extend(self._as_list(specification.get("extension_behaviours")))
        extension_sources.extend(self._as_list(specification.get("exception_flows")))

        for item in extension_sources:
            description = self._extract_description(item) or self._extract_name(item)
            if not description:
                continue
            related = self._extract_related_ids(item)
            name = self._extract_name(item) or self._build_fallback_supporting_use_case(item, srs_json)
            if name:
                result.append(self._new_use_case(name, description, "extension", related))

        for requirement in self._as_list(srs_json.get("functional_requirements")):
            description = self._extract_description(requirement) or self._extract_name(requirement)
            req_id = self._extract_id(requirement)
            if not description:
                continue

            lowered = self._normalize_words(description)
            if not (self._has_any(lowered, self.OPTIONAL_WORDS) or self._has_any(lowered, self.ERROR_WORDS)):
                continue

            name = self._build_fallback_supporting_use_case(requirement, srs_json)
            if name:
                result.append(
                    self._new_use_case(
                        name=name,
                        description=description,
                        category="extension",
                        related=[req_id] if req_id else [],
                    )
                )

        for criterion in self._as_list(srs_json.get("acceptance_criteria")):
            description = self._extract_description(criterion) or self._extract_name(criterion)
            ac_id = self._extract_id(criterion)
            if not description:
                continue

            lowered = self._normalize_words(description)
            if not (self._has_any(lowered, self.OPTIONAL_WORDS) or self._has_any(lowered, self.ERROR_WORDS)):
                continue

            name = self._build_fallback_supporting_use_case(criterion, srs_json)
            if name:
                result.append(
                    self._new_use_case(
                        name=name,
                        description=description,
                        category="extension",
                        related=[ac_id] if ac_id else [],
                    )
                )

        return result

    def _build_relationships(
        self,
        actors: list[dict[str, Any]],
        main_use_cases: list[dict[str, Any]],
        included_use_cases: list[dict[str, Any]],
        extension_use_cases: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Build UML relationships with correct direction.
        """

        if not main_use_cases:
            return []

        base_uc_id = main_use_cases[0]["id"]
        relationships: list[dict[str, Any]] = []

        for actor in actors:
            relationships.append({
                "from": actor["id"],
                "to": base_uc_id,
                "type": "association",
                "label": "",
                "related_requirements": [],
            })

        for included in included_use_cases:
            relationships.append({
                "from": base_uc_id,
                "to": included["id"],
                "type": "include",
                "label": "",
                "related_requirements": included.get("related_requirements", []),
            })

        for extension in extension_use_cases:
            relationships.append({
                "from": extension["id"],
                "to": base_uc_id,
                "type": "extend",
                "label": "",
                "related_requirements": extension.get("related_requirements", []),
            })

        return relationships

    def _build_analysis(
        self,
        specification: dict[str, Any],
        actors: list[dict[str, Any]],
        main_use_cases: list[dict[str, Any]],
        included_use_cases: list[dict[str, Any]],
        extension_use_cases: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build analysis JSON compatible with the existing agent output.
        """

        traceability: list[dict[str, Any]] = []

        for use_case in main_use_cases + included_use_cases + extension_use_cases:
            for req_id in use_case.get("related_requirements", []):
                traceability.append({
                    "source_id": req_id,
                    "source_type": self._guess_source_type(req_id),
                    "mapped_to": use_case.get("name", use_case.get("id")),
                    "mapping_type": "use_case",
                })

        for relationship in relationships:
            for req_id in relationship.get("related_requirements", []):
                traceability.append({
                    "source_id": req_id,
                    "source_type": self._guess_source_type(req_id),
                    "mapped_to": f"{relationship.get('from')} -> {relationship.get('to')}",
                    "mapping_type": relationship.get("type", "relationship"),
                })

        return {
            "feature_goal": main_use_cases[0].get("description", "") if main_use_cases else "",
            "primary_actors": [actor["name"] for actor in actors if actor.get("type") == "primary"],
            "secondary_actors": [actor["name"] for actor in actors if actor.get("type") != "primary"],
            "main_success_scenario": [uc.get("description", uc.get("name")) for uc in main_use_cases],
            "mandatory_included_behaviours": [
                {
                    "name": uc.get("name"),
                    "reason": uc.get("description"),
                    "related_requirements": uc.get("related_requirements", []),
                }
                for uc in included_use_cases
            ],
            "alternative_flows": [
                {
                    "name": uc.get("name"),
                    "condition": uc.get("description"),
                    "related_requirements": uc.get("related_requirements", []),
                }
                for uc in extension_use_cases
                if not self._has_any(self._normalize_words(uc.get("description", "")), self.ERROR_WORDS)
            ],
            "exception_flows": [
                {
                    "name": uc.get("name"),
                    "condition": uc.get("description"),
                    "related_requirements": uc.get("related_requirements", []),
                }
                for uc in extension_use_cases
                if self._has_any(self._normalize_words(uc.get("description", "")), self.ERROR_WORDS)
            ],
            "validation_flows": [
                {
                    "name": uc.get("name"),
                    "rule": uc.get("description"),
                    "related_requirements": uc.get("related_requirements", []),
                }
                for uc in included_use_cases
                if any(str(req).startswith("VR") for req in uc.get("related_requirements", []))
            ],
            "security_flows": [],
            "diagram_notes": [],
            "traceability": traceability,
        }

    # ------------------------------------------------------------------
    # Naming helpers
    # ------------------------------------------------------------------

    def _build_fallback_supporting_use_case(self, requirement: Any, srs_json: dict[str, Any]) -> str:
        """
        Name one fallback supporting (included/extension) use case for an
        SRS requirement/rule/criterion (fallback path only).

        Best-effort: look for a user story whose goal shares the most
        stemmed-token overlap with the requirement text, and use that
        already-clean, action-oriented `goal` phrase. When no story matches,
        fall back to one gentle pass over the requirement text itself via
        _clean_use_case_name (strip a common boilerplate lead-in, keep
        ~5 words, title-case) -- deliberately no multi-pass regex
        verb/topic extraction, which is what produced garbled names
        elsewhere in this module.
        """

        description = self._extract_description(requirement) or self._extract_name(requirement)
        if not description:
            return ""

        matched_goal = self._best_matching_user_story_goal(description, srs_json)
        return self._clean_use_case_name(matched_goal or description)

    def _best_matching_user_story_goal(self, requirement_text: str, srs_json: dict[str, Any]) -> str:
        requirement_stems = self._name_stems(requirement_text)
        if not requirement_stems:
            return ""

        best_goal = ""
        best_overlap = 0

        for story in self._as_list(srs_json.get("user_stories")):
            if not isinstance(story, dict):
                continue
            goal = str(story.get("goal", "")).strip()
            if not goal:
                continue
            goal_stems = self._name_stems(goal)
            if not goal_stems:
                continue
            overlap = len(requirement_stems & goal_stems)
            if overlap > best_overlap:
                best_overlap = overlap
                best_goal = goal

        return best_goal

    def _new_use_case(self, name: str, description: str, category: str, related: list[str]) -> dict[str, Any]:
        return {
            "id": "",  # assigned later
            "name": self._clean_use_case_name(name),
            "description": description or name,
            "category": category,
            "related_requirements": self._unique([str(item) for item in related if item]),
        }

    # Standalone filler words that would otherwise survive gentle truncation
    # as a leftover fragment (e.g. "Validate The User Credentials Against").
    # Mirrors usecase_validator.py's FRAGMENT_WORDS check -- kept as a
    # separate copy per this codebase's convention of not sharing files
    # between these deterministic agent modules.
    NAME_FILLER_WORDS = {
        "a", "an", "the", "this", "that", "these", "those", "their", "its",
        "his", "her", "our", "your", "my", "can", "could", "would", "should",
        "given", "when", "then",
    }

    def _clean_use_case_name(self, name: str) -> str:
        cleaned = self._remove_requirement_noise(name)
        cleaned = re.sub(r"[^a-zA-Z0-9 ]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        words = [word for word in cleaned.split() if word.lower() not in self.NAME_FILLER_WORDS]

        if not words:
            return "Perform Feature Action"

        # Keep visible UML labels short.
        cleaned = " ".join(words[:5])
        return self._title_case(cleaned)

    # ------------------------------------------------------------------
    # Deduplication and IDs
    # ------------------------------------------------------------------

    # Small, purpose-scoped stopword set for name-similarity dedup only --
    # deliberately separate from usecase_validator.py's STOPWORDS (that one
    # is tuned for out-of-scope stem matching, a different job).
    DEDUP_STOPWORDS = {
        "the", "a", "an", "and", "or", "to", "via", "by", "for", "of", "in",
        "on", "with", "only", "is", "are", "be", "this", "that", "flow",
        "feature", "process", "scope", "out", "from", "as", "at", "using",
    }

    # Jaccard overlap threshold (on stemmed name tokens) above which two use
    # cases are treated as naming the same real behaviour.
    NAME_SIMILARITY_THRESHOLD = 0.6

    def _merge_near_duplicates(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Three passes, cheapest/most-certain first:
        1. Exact normalized-name match (today's original behaviour).
        2. Identical, non-empty related_requirements sets -- two use cases
           citing the exact same SRS requirement ids are almost certainly the
           same real behaviour regardless of wording (catches synonym-level
           duplicates like "Initiate Forgot Password Process" vs "Initiate
           Recovery Flow" citing the same FR, which no name-similarity
           metric would catch, since they share no meaningful stems).
        3. Stem/token Jaccard overlap on names above NAME_SIMILARITY_THRESHOLD
           (catches paraphrase-level near-duplicates the first two passes
           miss, e.g. differently-worded restatements of the same action).
        """
        merged = self._dedupe_by_exact_name(items)
        merged = self._dedupe_by_shared_requirements(merged)
        merged = self._dedupe_by_name_similarity(merged)
        return merged

    def _merge_near_duplicates_across_categories(
        self,
        included_use_cases: list[dict[str, Any]],
        extension_use_cases: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Run _merge_near_duplicates over included+extension combined, then
        split back by each surviving item's own "category" field -- a
        duplicate can span the include/extend boundary (two differently-
        categorized entries naming the same real behaviour), which per-list
        deduping alone cannot catch. When a duplicate does span the
        boundary, the first-seen item's category wins (included is listed
        first below, so an included/extension collision resolves to
        included -- the more conservative, mandatory-by-default choice).
        """

        combined = included_use_cases + extension_use_cases
        merged = self._merge_near_duplicates(combined)

        merged_included = [item for item in merged if item.get("category") != "extension"]
        merged_extension = [item for item in merged if item.get("category") == "extension"]

        return merged_included, merged_extension

    def _dedupe_by_exact_name(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}

        for item in items:
            name = self._clean_use_case_name(item.get("name", ""))
            if not name:
                continue
            key = self._normalize_words(name)

            if key not in merged:
                merged[key] = dict(item)
                merged[key]["name"] = name
                merged[key]["related_requirements"] = self._unique(item.get("related_requirements", []))
                continue

            merged[key] = self._merge_two_use_cases(merged[key], item)

        return list(merged.values())

    def _dedupe_by_shared_requirements(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: list[tuple[frozenset, int]] = []

        for item in items:
            related = frozenset(str(r) for r in item.get("related_requirements", []) if r)

            match_index = None
            if related:
                match_index = next((index for existing, index in seen if existing == related), None)

            if match_index is not None:
                result[match_index] = self._merge_two_use_cases(result[match_index], item)
                continue

            result.append(dict(item))
            if related:
                seen.append((related, len(result) - 1))

        return result

    def _dedupe_by_name_similarity(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        result_stems: list[set[str]] = []

        for item in items:
            stems = self._name_stems(item.get("name", ""))

            match_index = None
            if stems:
                for index, existing_stems in enumerate(result_stems):
                    if not existing_stems:
                        continue
                    overlap = stems & existing_stems
                    union = stems | existing_stems
                    if union and len(overlap) / len(union) >= self.NAME_SIMILARITY_THRESHOLD:
                        match_index = index
                        break

            if match_index is not None:
                result[match_index] = self._merge_two_use_cases(result[match_index], item)
                continue

            result.append(dict(item))
            result_stems.append(stems)

        return result

    def _merge_two_use_cases(self, existing: dict[str, Any], new_item: dict[str, Any]) -> dict[str, Any]:
        existing = dict(existing)
        existing["related_requirements"] = self._unique(
            existing.get("related_requirements", []) + new_item.get("related_requirements", [])
        )

        existing_description = str(existing.get("description", ""))
        new_description = str(new_item.get("description", ""))
        if new_description and new_description not in existing_description:
            existing["description"] = (
                f"{existing_description} | {new_description}" if existing_description else new_description
            )

        return existing

    def _name_stems(self, name: str) -> set[str]:
        words = re.findall(r"[a-zA-Z0-9]+", str(name).lower())
        return {self._stem_word(word) for word in words if word not in self.DEDUP_STOPWORDS and len(word) >= 3}

    def _stem_word(self, word: str) -> str:
        word = word.lower()

        # Very small generic stemmer -- mirrors usecase_validator.py's own
        # _stem (kept as a separate copy per this codebase's convention of
        # not sharing files between these deterministic agent modules).
        if word.startswith("verif"):
            return "verif"
        if word.startswith("initiat"):
            return "initiat"

        for suffix in ["ations", "ation", "itions", "ition", "ments", "ment", "ing", "ed", "es", "s"]:
            if word.endswith(suffix) and len(word) > len(suffix) + 3:
                return word[: -len(suffix)]

        return word

    def _renumber_use_cases(
        self,
        main_use_cases: list[dict[str, Any]],
        included_use_cases: list[dict[str, Any]],
        extension_use_cases: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        counter = 1

        for collection in [main_use_cases, included_use_cases, extension_use_cases]:
            for use_case in collection:
                use_case["id"] = f"UC-{counter:03d}"
                counter += 1

        return main_use_cases, included_use_cases, extension_use_cases

    # ------------------------------------------------------------------
    # Generic helper methods
    # ------------------------------------------------------------------

    def _get_feature_name(self, srs_json: dict[str, Any], sds_json: dict[str, Any]) -> str:
        return (
            srs_json.get("feature_name")
            or sds_json.get("document_control", {}).get("feature_name")
            or sds_json.get("feature_name")
            or "Feature"
        )

    def _get_design_view(self, sds_json: dict[str, Any], view_name: str) -> dict[str, Any]:
        design_views = sds_json.get("design_views", {})
        view = design_views.get(view_name, {})
        return view if isinstance(view, dict) else {}

    def _get_text(self, data: dict[str, Any], key: str) -> str:
        value = data.get(key, "")
        if isinstance(value, str):
            return value.strip()
        return str(value).strip() if value is not None else ""

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _extract_name(self, item: Any) -> str:
        if isinstance(item, dict):
            return str(
                item.get("name")
                or item.get("actor")
                or item.get("role")
                or item.get("title")
                or item.get("use_case")
                or ""
            ).strip()
        return str(item).strip()

    def _extract_description(self, item: Any) -> str:
        if isinstance(item, dict):
            return str(
                item.get("description")
                or item.get("goal")
                or item.get("reason")
                or item.get("condition")
                or item.get("rule")
                or item.get("expectation")
                or item.get("payload")
                or item.get("risk")
                or item.get("mitigation")
                or ""
            ).strip()
        return str(item).strip()

    def _extract_id(self, item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get("id", "")).strip()
        return ""

    def _extract_related_ids(self, item: Any) -> list[str]:
        if not isinstance(item, dict):
            return []
        related = item.get("related_requirements", [])
        if isinstance(related, list):
            return [str(value) for value in related if value]
        if related:
            return [str(related)]
        item_id = self._extract_id(item)
        return [item_id] if item_id else []

    def _collect_ids(self, items: list[Any]) -> list[str]:
        ids = []
        for item in self._as_list(items):
            item_id = self._extract_id(item)
            if item_id:
                ids.append(item_id)
        return self._unique(ids)

    def _is_technical_actor(self, name: str) -> bool:
        lowered = self._normalize_words(name)
        return any(word in lowered for word in self.TECHNICAL_ACTOR_WORDS)

    def _remove_requirement_noise(self, text: str) -> str:
        cleaned = str(text).strip()
        cleaned = re.sub(r"^given\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^when\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^then\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(the system must|system must|system shall|the user must|user must|must|shall|should)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(allow|enable|let|provide|support)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("'", "")
        return cleaned.strip()

    def _normalize_words(self, text: str) -> str:
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _has_any(self, text: str, words: list[str]) -> bool:
        normalized = self._normalize_words(text)
        return any(word in normalized for word in words)

    def _unique(self, items: list[str]) -> list[str]:
        result = []
        for item in items:
            value = str(item).strip()
            if value and value not in result:
                result.append(value)
        return result

    def _title_case(self, text: str) -> str:
        return " ".join(word[:1].upper() + word[1:] for word in str(text).split())

    def _guess_source_type(self, requirement_id: str) -> str:
        requirement_id = str(requirement_id)
        if requirement_id.startswith("FR"):
            return "FR"
        if requirement_id.startswith("AC"):
            return "AC"
        if requirement_id.startswith("VR"):
            return "VR"
        if requirement_id.startswith("NFR"):
            return "NFR"
        return "Requirement"
