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

    GENERIC_USE_CASE_NAMES = [
        "use feature", "use the feature", "manage feature", "access feature",
        "perform feature", "do feature", "feature action", "use system",
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

    COMMON_FIELDS = [
        "credentials", "credential", "email", "password", "username", "token",
        "jwt", "quantity", "price", "amount", "date", "phone", "name",
        "address", "role", "status", "total",
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
        main_use_cases = self._build_main_use_cases(specification, srs_json)
        included_use_cases = self._build_included_use_cases(specification, srs_json)
        extension_use_cases = self._build_extension_use_cases(specification, srs_json)

        included_use_cases = self._dedupe_and_merge(included_use_cases)
        extension_use_cases = self._dedupe_and_merge(extension_use_cases)

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
        Normalize LLM specification and fill missing values from SRS/SDS.
        """

        feature_name = self._get_feature_name(srs_json, sds_json)
        business_goal = self._get_text(srs_json, "business_goal")

        return {
            "system_boundary": specification.get("system_boundary") or f"{feature_name} Feature",
            "diagram_title": specification.get("diagram_title") or f"{feature_name} Use Case Diagram",
            "actors": specification.get("actors") or specification.get("primary_actors") or srs_json.get("user_roles", []),
            "primary_use_cases": specification.get("primary_use_cases") or specification.get("main_use_cases") or [
                {
                    "name": self._build_main_use_case_name(feature_name, business_goal),
                    "description": business_goal or f"Main user goal for the {feature_name} feature.",
                    "related_requirements": self._collect_ids(srs_json.get("functional_requirements", [])),
                }
            ],
            "included_behaviours": specification.get("included_behaviours") or specification.get("mandatory_included_behaviours") or [],
            "extension_behaviours": specification.get("extension_behaviours") or specification.get("alternative_flows") or [],
            "exception_flows": specification.get("exception_flows") or [],
            "traceability": specification.get("traceability", []),
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

    def _build_main_use_cases(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build the main use case.
        """

        feature_name = self._get_feature_name(srs_json, {})
        business_goal = self._get_text(srs_json, "business_goal")
        primary_items = self._as_list(specification.get("primary_use_cases")) or []

        if not primary_items:
            primary_items = [{
                "name": self._build_main_use_case_name(feature_name, business_goal),
                "description": business_goal or f"Main user goal for the {feature_name} feature.",
                "related_requirements": self._collect_ids(srs_json.get("functional_requirements", [])),
            }]

        result = []
        for item in primary_items[:1]:  # Feature-level diagram should have one main user goal.
            name = self._extract_name(item)
            if self._is_generic_use_case_name(name):
                name = self._build_main_use_case_name(feature_name, business_goal)

            result.append({
                "id": "UC-001",
                "name": self._clean_use_case_name(name),
                "description": self._extract_description(item) or business_goal or f"Main user goal for the {feature_name} feature.",
                "category": "main",
                "related_requirements": self._extract_related_ids(item) or self._collect_ids(srs_json.get("functional_requirements", [])),
            })

        return result

    def _build_included_use_cases(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build included use cases from mandatory behaviours and validation rules.
        """

        result: list[dict[str, Any]] = []

        for item in self._as_list(specification.get("included_behaviours")):
            description = self._extract_description(item) or self._extract_name(item)
            related = self._extract_related_ids(item)
            name = self._extract_name(item) or self._make_action_name(description)
            if name:
                result.append(self._new_use_case(name, description, "included", related))

        for rule in self._as_list(srs_json.get("validation_rules")):
            rule_text = self._extract_description(rule) or self._extract_name(rule)
            rule_id = self._extract_id(rule)
            if rule_text:
                result.append(
                    self._new_use_case(
                        name=self._make_validation_use_case_name(rule_text),
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

            name = self._make_action_name(description)
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
        Build extension use cases from optional, alternative, recovery, and error flows.
        """

        result: list[dict[str, Any]] = []

        extension_sources = []
        extension_sources.extend(self._as_list(specification.get("extension_behaviours")))
        extension_sources.extend(self._as_list(specification.get("exception_flows")))

        for item in extension_sources:
            description = self._extract_description(item) or self._extract_name(item)
            related = self._extract_related_ids(item)
            name = self._extract_name(item) or self._make_extension_name(description)
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

            result.append(
                self._new_use_case(
                    name=self._make_extension_name(description),
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

            result.append(
                self._new_use_case(
                    name=self._make_extension_name(description),
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

    def _build_main_use_case_name(self, feature_name: str, business_goal: str) -> str:
        """
        Build the main use case name.

        For a feature-level diagram, the feature name is normally the cleanest
        standard main use case name, for example Login, Checkout, Manage Cart,
        Enroll in Course.
        """

        if feature_name and not self._is_generic_use_case_name(feature_name):
            return self._clean_use_case_name(feature_name)

        if business_goal:
            cleaned = self._remove_requirement_noise(business_goal)
            cleaned = re.sub(r"^(allow|enable|let|provide)\s+", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\b(users?|customers?|admins?|students?|instructors?)\b\s+to\s+", "", cleaned, flags=re.IGNORECASE).strip()
            return self._clean_use_case_name(cleaned)

        return "Perform Feature Action"

    def _make_validation_use_case_name(self, text: str) -> str:
        field = self._infer_field_name(text)
        if field:
            return f"Validate {field}"
        return "Validate Input"

    def _make_action_name(self, text: str) -> str:
        lowered = self._normalize_words(text)

        if self._has_any(lowered, ["validate", "verify", "check"]):
            field = self._infer_field_name(text)
            if field:
                return f"Validate {field}"
            return "Validate Input"

        if self._has_any(lowered, ["generate", "create"]):
            field = self._infer_field_name(text)
            if field:
                return f"Generate {field}"
            return "Generate Result"

        if "calculate" in lowered:
            field = self._infer_field_name(text) or "Total"
            return f"Calculate {field}"

        cleaned = self._remove_requirement_noise(text)
        match = re.search(
            r"\b(validate|verify|check|calculate|generate|create|save|store|retrieve|process|submit|confirm|apply|update|delete|return)\b\s+(.+)",
            cleaned,
            flags=re.IGNORECASE,
        )

        if match:
            verb = match.group(1)
            target = self._short_topic(match.group(2), default="Required Behaviour")
            return self._clean_use_case_name(f"{verb} {target}")

        return self._clean_use_case_name(cleaned)

    def _make_extension_name(self, text: str) -> str:
        lowered = self._normalize_words(text)

        if self._has_any(lowered, self.ERROR_WORDS):
            topic = self._extract_error_topic(text)
            return self._clean_use_case_name(f"Handle {topic}")

        if self._has_any(lowered, ["forgot", "recover", "recovery", "reset", "retry", "initiate", "link", "redirect", "direct"]):
            topic = self._extract_recovery_topic(text)
            return self._clean_use_case_name(f"Initiate {topic}")

        topic = self._short_topic(text, default="Alternative Flow")
        return self._clean_use_case_name(topic)

    def _infer_field_name(self, text: str) -> str:
        lowered = self._normalize_words(text)

        # Prefer stronger domain nouns if present in the requirement text.
        if "credential" in lowered:
            return "Credentials"
        if "jwt" in lowered or "token" in lowered:
            return "Token"

        for field in self.COMMON_FIELDS:
            if field in lowered:
                return self._title_case(field)

        return ""

    def _extract_error_topic(self, text: str) -> str:
        cleaned = self._remove_requirement_noise(text)
        lowered = cleaned.lower()

        for word in ["invalid", "incorrect", "failed", "failure", "denied", "unauthorized", "forbidden", "error"]:
            match = re.search(rf"\b{word}\b\s+([a-zA-Z0-9 ]{{1,40}})", lowered)
            if match:
                return self._short_topic(f"{word} {match.group(1)}", default="Exception")

        return self._short_topic(cleaned, default="Exception")

    def _extract_recovery_topic(self, text: str) -> str:
        cleaned = self._remove_requirement_noise(text)
        lowered = cleaned.lower()

        match = re.search(r"\binitiat(?:e|es|ion)\b\s+(?:the\s+)?([a-zA-Z0-9 ]{1,50})", lowered)
        if match:
            return self._short_topic(match.group(1), default="Recovery Flow")

        match = re.search(r"\b(forgot|recover|recovery|reset|retry)\b\s+([a-zA-Z0-9 ]{0,40})", lowered)
        if match:
            return self._short_topic(f"{match.group(1)} {match.group(2)}", default="Recovery Flow")

        return "Recovery Flow"

    def _new_use_case(self, name: str, description: str, category: str, related: list[str]) -> dict[str, Any]:
        return {
            "id": "",  # assigned later
            "name": self._clean_use_case_name(name),
            "description": description or name,
            "category": category,
            "related_requirements": self._unique([str(item) for item in related if item]),
        }

    def _clean_use_case_name(self, name: str) -> str:
        cleaned = self._remove_requirement_noise(name)
        cleaned = re.sub(r"[^a-zA-Z0-9 ]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        words = cleaned.split()

        if not words:
            return "Perform Feature Action"

        # Keep visible UML labels short.
        cleaned = " ".join(words[:5])
        return self._title_case(cleaned)

    def _short_topic(self, text: str, default: str) -> str:
        cleaned = self._remove_requirement_noise(text)
        cleaned = re.sub(
            r"\b(the system must|system must|must|shall|should|user|users|actor|actors|clicks|click|given|when|then|using|with|against|provided|provide|return|returns|display|displays|direct|directs|redirect|redirects|link|mechanism)\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
        words = cleaned.split()
        if not words:
            return default
        return " ".join(words[:4])

    # ------------------------------------------------------------------
    # Deduplication and IDs
    # ------------------------------------------------------------------

    def _dedupe_and_merge(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

            merged[key]["related_requirements"] = self._unique(
                merged[key].get("related_requirements", []) + item.get("related_requirements", [])
            )

            existing_description = str(merged[key].get("description", ""))
            new_description = str(item.get("description", ""))
            if new_description and new_description not in existing_description:
                merged[key]["description"] = f"{existing_description} | {new_description}" if existing_description else new_description

        return list(merged.values())

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

    def _is_generic_use_case_name(self, name: str) -> bool:
        lowered = self._normalize_words(name)
        return not lowered or lowered in self.GENERIC_USE_CASE_NAMES or re.fullmatch(r"use .+ feature", lowered) is not None

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
