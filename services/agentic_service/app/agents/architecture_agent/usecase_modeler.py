"""
Architecture Agent Use Case Modeler.

Purpose:
This file creates a standard UML use case model from approved SRS/SDS data.

Why this file exists:
- The LLM should not directly control the final PlantUML diagram.
- The LLM may identify actors, goals, scenarios, and conditions.
- This modeler normalizes that information into a consistent UML model.
- The backend then validates and converts the model into PlantUML.

Design principle:
This file is feature-independent. It does not hardcode Login, Cart, Payment,
LMS, or any other feature. It reads the approved SRS/SDS and creates the
best possible feature-level use case model from those artifacts.
"""

from __future__ import annotations

import re
from typing import Any


class ArchitectureUseCaseModeler:
    """
    Builds usecase_analysis_json and usecase_json from a use case specification.

    The input specification may come from the LLM. If it is missing or weak,
    the modeler derives the model from the approved SRS and SDS.
    """

    TECHNICAL_ACTOR_WORDS = [
        "database",
        "mongodb",
        "mysql",
        "postgres",
        "api",
        "endpoint",
        "controller",
        "server",
        "backend",
        "frontend",
        "react",
        "node",
        "express",
        "jwt",
        "library",
        "service layer",
        "model",
        "view",
        "collection",
        "table",
        "schema",
    ]

    GENERIC_USE_CASE_NAMES = [
        "use feature",
        "use the feature",
        "manage feature",
        "access feature",
        "perform feature",
        "use login feature",
    ]

    OPTIONAL_WORDS = [
        "optional",
        "alternative",
        "forgot",
        "recover",
        "recovery",
        "reset",
        "retry",
        "re-enter",
        "cancel",
        "skip",
        "if",
        "when",
        "unless",
    ]

    ERROR_WORDS = [
        "invalid",
        "error",
        "failed",
        "failure",
        "prevent",
        "denied",
        "unauthorized",
        "not found",
        "incorrect",
        "exception",
        "timeout",
    ]

    MANDATORY_BEHAVIOUR_WORDS = [
        "validate",
        "verify",
        "check",
        "calculate",
        "generate",
        "create",
        "save",
        "store",
        "retrieve",
        "return",
        "authenticate",
        "authorize",
        "process",
        "submit",
        "confirm",
    ]

    def build(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
        usecase_specification_json: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Build usecase_analysis_json and final usecase_json.

        Args:
            srs_json:
                Approved SRS JSON or enhanced SRS JSON.

            sds_json:
                Approved/generated SDS JSON.

            usecase_specification_json:
                LLM-provided intermediate use case specification.
                If missing or incomplete, the modeler derives from SRS/SDS.

        Returns:
            tuple(usecase_analysis_json, usecase_json)
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
        notes = self._build_notes(specification, srs_json, sds_json)

        use_cases = []
        use_cases.extend(main_use_cases)
        use_cases.extend(included_use_cases)
        use_cases.extend(extension_use_cases)
        use_cases = self._dedupe_by_name(use_cases)

        relationships = self._build_relationships(
            actors=actors,
            main_use_cases=main_use_cases,
            included_use_cases=included_use_cases,
            extension_use_cases=extension_use_cases,
        )

        notes = self._attach_notes_to_main_use_case(notes, main_use_cases)

        usecase_json = {
            "system_boundary": specification["system_boundary"],
            "diagram_title": specification["diagram_title"],
            "actors": actors,
            "use_cases": use_cases,
            "relationships": relationships,
            "notes": notes,
            "standards_notes": [
                "Actors are external roles or external systems outside the feature boundary.",
                "Use cases are user-goal behaviours inside the feature boundary.",
                "<<include>> is used for mandatory behaviour required by the base use case.",
                "<<extend>> is used for optional, alternative, recovery, or exception behaviour.",
                "Constraints, NFRs, and risks are represented as notes instead of normal use cases.",
            ],
        }

        usecase_analysis_json = self._build_analysis(
            specification=specification,
            actors=actors,
            main_use_cases=main_use_cases,
            included_use_cases=included_use_cases,
            extension_use_cases=extension_use_cases,
            notes=notes,
            relationships=relationships,
        )

        return usecase_analysis_json, usecase_json

    def _normalize_specification(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
        specification: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize LLM specification and fill missing parts from SRS/SDS.
        """

        feature_name = self._get_feature_name(srs_json, sds_json)
        business_goal = self._get_text(srs_json, "business_goal")

        system_boundary = specification.get("system_boundary") or f"{feature_name} Feature"
        diagram_title = specification.get("diagram_title") or f"{feature_name} Use Case Diagram"

        actors = specification.get("actors") or specification.get("primary_actors") or srs_json.get("user_roles", [])

        primary_use_cases = specification.get("primary_use_cases") or specification.get("main_use_cases") or []
        if not primary_use_cases:
            primary_use_cases = [
                {
                    "name": self._build_main_use_case_name(feature_name, business_goal),
                    "description": business_goal or f"Main goal of the {feature_name} feature.",
                    "related_requirements": self._collect_ids(srs_json.get("functional_requirements", [])),
                }
            ]

        included_behaviours = specification.get("included_behaviours") or specification.get("mandatory_included_behaviours") or []
        extension_behaviours = specification.get("extension_behaviours") or specification.get("alternative_flows") or []
        exception_flows = specification.get("exception_flows") or []
        constraint_notes = specification.get("constraint_notes") or specification.get("diagram_notes") or []

        return {
            "system_boundary": system_boundary,
            "diagram_title": diagram_title,
            "actors": actors,
            "primary_use_cases": primary_use_cases,
            "included_behaviours": included_behaviours,
            "extension_behaviours": extension_behaviours,
            "exception_flows": exception_flows,
            "constraint_notes": constraint_notes,
            "traceability": specification.get("traceability", []),
        }

    def _build_actors(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build actors from SRS roles, LLM specification, and SDS context view.
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
                names.append(name)

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
        Build main use case list.
        """

        result = []
        primary_items = self._as_list(specification.get("primary_use_cases"))
        feature_name = self._get_feature_name(srs_json, {})
        business_goal = self._get_text(srs_json, "business_goal")

        if not primary_items:
            primary_items = [{
                "name": self._build_main_use_case_name(feature_name, business_goal),
                "description": business_goal,
                "related_requirements": self._collect_ids(srs_json.get("functional_requirements", [])),
            }]

        for index, item in enumerate(primary_items, start=1):
            name = self._extract_name(item)
            if self._is_generic_use_case_name(name):
                name = self._build_main_use_case_name(feature_name, business_goal)

            result.append({
                "id": f"UC-{index:03d}",
                "name": name,
                "description": self._extract_description(item) or business_goal or f"Main behaviour for {feature_name}.",
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

        result = []
        seen_names = set()
        counter = 50

        for item in self._as_list(specification.get("included_behaviours")):
            name = self._extract_name(item)
            description = self._extract_description(item)
            related = self._extract_related_ids(item)
            if not name:
                name = self._make_action_name(description)
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            result.append({
                "id": f"UC-{counter:03d}",
                "name": name,
                "description": description or name,
                "category": "included",
                "related_requirements": related,
            })
            counter += 1

        for rule in self._as_list(srs_json.get("validation_rules")):
            rule_text = self._extract_description(rule) or self._extract_name(rule)
            rule_id = self._extract_id(rule)
            if not rule_text:
                continue
            name = self._make_validation_use_case_name(rule_text)
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            result.append({
                "id": f"UC-{counter:03d}",
                "name": name,
                "description": rule_text,
                "category": "included",
                "related_requirements": [rule_id] if rule_id else [],
            })
            counter += 1

        for requirement in self._as_list(srs_json.get("functional_requirements")):
            description = self._extract_description(requirement) or self._extract_name(requirement)
            req_id = self._extract_id(requirement)
            if not description:
                continue
            lowered = description.lower()
            if self._has_any(lowered, self.OPTIONAL_WORDS) or self._has_any(lowered, self.ERROR_WORDS):
                continue
            if not self._has_any(lowered, self.MANDATORY_BEHAVIOUR_WORDS):
                continue
            name = self._make_action_name(description)
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            result.append({
                "id": f"UC-{counter:03d}",
                "name": name,
                "description": description,
                "category": "included",
                "related_requirements": [req_id] if req_id else [],
            })
            counter += 1

        return result

    def _build_extension_use_cases(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build extension use cases from optional, alternative, recovery, and error flows.
        """

        result = []
        seen_names = set()
        counter = 100

        extension_sources = []
        extension_sources.extend(self._as_list(specification.get("extension_behaviours")))
        extension_sources.extend(self._as_list(specification.get("exception_flows")))

        for item in extension_sources:
            name = self._extract_name(item)
            description = self._extract_description(item)
            related = self._extract_related_ids(item)
            if not name:
                name = self._make_extension_name(description)
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            result.append({
                "id": f"UC-{counter:03d}",
                "name": name,
                "description": description or name,
                "category": "extension",
                "related_requirements": related,
            })
            counter += 1

        for requirement in self._as_list(srs_json.get("functional_requirements")):
            description = self._extract_description(requirement) or self._extract_name(requirement)
            req_id = self._extract_id(requirement)
            if not description:
                continue
            lowered = description.lower()
            if not self._has_any(lowered, self.OPTIONAL_WORDS):
                continue
            name = self._make_extension_name(description)
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            result.append({
                "id": f"UC-{counter:03d}",
                "name": name,
                "description": description,
                "category": "extension",
                "related_requirements": [req_id] if req_id else [],
            })
            counter += 1

        for criterion in self._as_list(srs_json.get("acceptance_criteria")):
            description = self._extract_description(criterion) or self._extract_name(criterion)
            ac_id = self._extract_id(criterion)
            if not description:
                continue
            lowered = description.lower()
            if not self._has_any(lowered, self.OPTIONAL_WORDS + self.ERROR_WORDS):
                continue
            name = self._make_extension_name(description)
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            result.append({
                "id": f"UC-{counter:03d}",
                "name": name,
                "description": description,
                "category": "extension",
                "related_requirements": [ac_id] if ac_id else [],
            })
            counter += 1

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

        relationships = []
        if not main_use_cases:
            return relationships

        base_uc_id = main_use_cases[0]["id"]

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
                "label": "mandatory",
                "related_requirements": included.get("related_requirements", []),
            })

        for extension in extension_use_cases:
            relationships.append({
                "from": extension["id"],
                "to": base_uc_id,
                "type": "extend",
                "label": "optional/conditional",
                "related_requirements": extension.get("related_requirements", []),
            })

        return relationships

    def _build_notes(
        self,
        specification: dict[str, Any],
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build compact notes from constraints, NFRs, risks, and specification notes.
        """

        note_parts = []
        related_ids = []

        for note in self._as_list(specification.get("constraint_notes")):
            note_text = self._extract_description(note) or self._extract_name(note)
            if note_text:
                note_parts.append(note_text)
                related_ids.extend(self._extract_related_ids(note))

        constraints = self._as_list(srs_json.get("constraints"))
        if constraints:
            note_parts.append("Constraints: " + self._short_join([self._stringify(item) for item in constraints]))

        nfrs = self._as_list(srs_json.get("non_functional_requirements"))
        if nfrs:
            note_parts.append("NFRs: " + self._short_join([self._extract_description(item) or self._stringify(item) for item in nfrs]))
            related_ids.extend(self._collect_ids(nfrs))

        risks = self._as_list(srs_json.get("risks"))
        if risks:
            note_parts.append("Risks: " + self._short_join([self._extract_description(item) or self._stringify(item) for item in risks]))

        if not note_parts:
            return []

        return [{
            "id": "NOTE-001",
            "target": "UC-001",
            "title": "Design Constraints and Quality Notes",
            "description": self._limit_text(" | ".join(note_parts), 420),
            "related_requirements": self._unique(related_ids),
        }]

    def _attach_notes_to_main_use_case(
        self,
        notes: list[dict[str, Any]],
        main_use_cases: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Make sure notes point to an existing use case.
        """

        if not notes or not main_use_cases:
            return notes

        main_id = main_use_cases[0]["id"]
        for note in notes:
            note["target"] = note.get("target") or main_id
            if note["target"] == "UC-001" and main_id != "UC-001":
                note["target"] = main_id

        return notes

    def _build_analysis(
        self,
        specification: dict[str, Any],
        actors: list[dict[str, Any]],
        main_use_cases: list[dict[str, Any]],
        included_use_cases: list[dict[str, Any]],
        extension_use_cases: list[dict[str, Any]],
        notes: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build analysis JSON compatible with the existing validator.
        """

        traceability = []

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

        for note in notes:
            for req_id in note.get("related_requirements", []):
                traceability.append({
                    "source_id": req_id,
                    "source_type": self._guess_source_type(req_id),
                    "mapped_to": note.get("title", note.get("id")),
                    "mapping_type": "note",
                })

        return {
            "feature_goal": specification.get("primary_use_cases", [{}])[0].get("description", ""),
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
                if not self._has_any(uc.get("description", "").lower(), self.ERROR_WORDS)
            ],
            "exception_flows": [
                {
                    "name": uc.get("name"),
                    "condition": uc.get("description"),
                    "related_requirements": uc.get("related_requirements", []),
                }
                for uc in extension_use_cases
                if self._has_any(uc.get("description", "").lower(), self.ERROR_WORDS)
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
            "diagram_notes": notes,
            "traceability": traceability,
        }

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
        for item in items:
            item_id = self._extract_id(item)
            if item_id:
                ids.append(item_id)
        return self._unique(ids)

    def _is_technical_actor(self, name: str) -> bool:
        lowered = name.lower()
        return any(word in lowered for word in self.TECHNICAL_ACTOR_WORDS)

    def _is_generic_use_case_name(self, name: str) -> bool:
        lowered = str(name).strip().lower()
        return not lowered or lowered in self.GENERIC_USE_CASE_NAMES

    def _build_main_use_case_name(self, feature_name: str, business_goal: str) -> str:
        """
        Build a generic action-oriented name.

        This is not feature-specific hardcoding. It tries to extract a verb phrase
        from the business goal. If that fails, it uses the feature name safely.
        """

        goal = business_goal.strip()
        if goal:
            cleaned = re.sub(r"^(allow|enable|let|provide)\s+", "", goal, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\b(users?|customers?|admins?|students?|instructors?)\b\s+to\s+", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\s+so that\s+.*$", "", cleaned, flags=re.IGNORECASE).strip()
            words = cleaned.split()
            if 1 <= len(words) <= 6:
                return self._title_case(cleaned)

        if feature_name:
            return self._title_case(feature_name)

        return "Perform Feature Action"

    def _make_validation_use_case_name(self, text: str) -> str:
        field = self._infer_field_name(text)
        if field:
            return f"Validate {field}"
        return "Validate Input"

    def _make_action_name(self, text: str) -> str:
        cleaned = self._remove_requirement_noise(text)
        cleaned = re.sub(r"^(the system must|system must|must|shall|should)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"^(allow|provide|support)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = cleaned.rstrip(".")
        words = cleaned.split()
        if len(words) > 6:
            cleaned = " ".join(words[:6])
        return self._title_case(cleaned) if cleaned else "Process Required Behaviour"

    def _make_extension_name(self, text: str) -> str:
        cleaned = self._remove_requirement_noise(text)
        lowered = cleaned.lower()
        if self._has_any(lowered, self.ERROR_WORDS):
            return "Handle " + self._title_case(self._short_topic(cleaned, default="Exception"))
        if self._has_any(lowered, ["forgot", "recover", "recovery", "reset"]):
            return "Initiate " + self._title_case(self._short_topic(cleaned, default="Recovery Flow"))
        return self._title_case(self._short_topic(cleaned, default="Alternative Flow"))

    def _infer_field_name(self, text: str) -> str:
        lowered = text.lower()
        common_fields = re.findall(r"\b(email|password|username|quantity|price|amount|date|phone|name|address|role|status|token)\b", lowered)
        if common_fields:
            return self._title_case(common_fields[0])
        return ""

    def _remove_requirement_noise(self, text: str) -> str:
        cleaned = str(text).strip()
        cleaned = re.sub(r"^given\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^when\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^then\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("'", "")
        return cleaned

    def _short_topic(self, text: str, default: str) -> str:
        cleaned = self._remove_requirement_noise(text)
        cleaned = re.sub(r"\b(the system must|system must|must|shall|should|user|users|clicks|click|given|when|then)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
        words = cleaned.split()
        if not words:
            return default
        return " ".join(words[:5])

    def _dedupe_by_name(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = set()
        result = []
        for item in items:
            name = str(item.get("name", "")).lower()
            if not name or name in seen:
                continue
            seen.add(name)
            result.append(item)
        return result

    def _short_join(self, values: list[str], limit_each: int = 100) -> str:
        compact = [self._limit_text(value, limit_each) for value in values if value]
        return "; ".join(compact[:5])

    def _limit_text(self, text: str, limit: int) -> str:
        text = str(text).strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _stringify(self, value: Any) -> str:
        if isinstance(value, dict):
            return value.get("description") or value.get("risk") or value.get("mitigation") or str(value)
        return str(value)

    def _has_any(self, text: str, words: list[str]) -> bool:
        return any(word in text for word in words)

    def _unique(self, items: list[str]) -> list[str]:
        result = []
        for item in items:
            if item and item not in result:
                result.append(item)
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
