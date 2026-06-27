"""
Architecture Agent Use Case Validator.

Purpose:
Validate generated UML Use Case model before PlantUML rendering.

Important:
- Feature-independent pass/fail validation.
- No quality score file.
- No hardcoded feature names such as Login, Cart, Payment, LMS.
- No domain-specific exception such as password reset special cases.
"""

from __future__ import annotations

import re
from typing import Any


class UseCaseValidationError(Exception):
    """
    Raised when the generated use case model is invalid or outside feature scope.
    """


class UseCaseQualityValidator:
    """
    Feature-independent validator for UML Use Case Diagram JSON.
    """

    TECHNICAL_ACTOR_TERMS = [
        "database", "mongodb", "mysql", "postgres", "collection", "table",
        "api", "endpoint", "controller", "service", "repository", "model",
        "schema", "server", "backend", "frontend", "react", "node",
        "express", "mongoose", "jwt", "token", "library", "middleware",
        "component", "page", "form",
    ]

    GENERIC_USE_CASE_NAMES = [
        "use feature", "use system", "manage feature", "access feature",
        "perform feature", "do feature", "feature action",
    ]

    NON_UML_USE_CASE_TERMS = [
        "response time", "performance", "responsive ui", "mern stack", "mvc",
        "architecture style", "database collection", "api endpoint",
    ]

    STOPWORDS = {
        "the", "a", "an", "and", "or", "to", "via", "by", "for", "of",
        "in", "on", "with", "only", "is", "are", "be", "this", "that",
        "flow", "feature", "scope", "out", "from", "as", "at", "using",
    }

    def validate(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
        usecase_analysis_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> None:
        errors: list[str] = []

        errors.extend(self._validate_basic_structure(usecase_json))
        errors.extend(self._validate_actors(usecase_json))
        errors.extend(self._validate_use_cases(usecase_json))
        errors.extend(self._validate_relationships(usecase_json))
        errors.extend(self._validate_traceability(srs_json, usecase_analysis_json, usecase_json))
        errors.extend(self._validate_out_of_scope(srs_json, usecase_json))

        if errors:
            raise UseCaseValidationError("; ".join(errors))

    def _validate_basic_structure(self, usecase_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        if not isinstance(usecase_json, dict):
            return ["usecase_json must be a JSON object."]

        required_keys = ["system_boundary", "diagram_title", "actors", "use_cases", "relationships", "notes"]

        for key in required_keys:
            if key not in usecase_json:
                errors.append(f"usecase_json missing required key: {key}")

        if not str(usecase_json.get("system_boundary", "")).strip():
            errors.append("Use case diagram must have a clear system boundary.")

        if not isinstance(usecase_json.get("actors", []), list) or not usecase_json.get("actors", []):
            errors.append("Use case diagram must have at least one actor.")

        if not isinstance(usecase_json.get("use_cases", []), list) or not usecase_json.get("use_cases", []):
            errors.append("Use case diagram must have at least one use case.")

        if not isinstance(usecase_json.get("relationships", []), list) or not usecase_json.get("relationships", []):
            errors.append("Use case diagram must have at least one relationship.")

        if not isinstance(usecase_json.get("notes", []), list):
            errors.append("usecase_json.notes must be a list.")

        return errors

    def _validate_actors(self, usecase_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        seen_actor_names: set[str] = set()

        for actor in usecase_json.get("actors", []):
            if not isinstance(actor, dict):
                errors.append("Each actor must be a JSON object.")
                continue

            actor_id = str(actor.get("id", "")).strip()
            actor_name = str(actor.get("name", "")).strip()

            if not actor_id or not actor_name:
                errors.append("Each actor must have id and name.")
                continue

            normalized_name = self._normalize(actor_name)

            if normalized_name in seen_actor_names:
                errors.append(f"Duplicate actor name found: {actor_name}")
            seen_actor_names.add(normalized_name)

            if self._contains_any(normalized_name, self.TECHNICAL_ACTOR_TERMS):
                errors.append(f"Technical component used as actor: {actor_name}")

        return errors

    def _validate_use_cases(self, usecase_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        seen_usecase_names: set[str] = set()

        for use_case in usecase_json.get("use_cases", []):
            if not isinstance(use_case, dict):
                errors.append("Each use case must be a JSON object.")
                continue

            use_case_id = str(use_case.get("id", "")).strip()
            use_case_name = str(use_case.get("name", "")).strip()

            if not use_case_id or not use_case_name:
                errors.append("Each use case must have id and name.")
                continue

            normalized_name = self._normalize(use_case_name)

            if normalized_name in seen_usecase_names:
                errors.append(f"Duplicate use case name found: {use_case_name}")
            seen_usecase_names.add(normalized_name)

            if normalized_name in self.GENERIC_USE_CASE_NAMES or re.fullmatch(r"use .+ feature", normalized_name):
                errors.append(f"Use case name is too generic: {use_case_name}")

            if self._contains_any(normalized_name, self.NON_UML_USE_CASE_TERMS):
                errors.append(
                    f"Non-functional requirement or technical constraint used as a normal use case: {use_case_name}"
                )

            if len(use_case_name.split()) > 6:
                errors.append(f"Use case name is too long for a standard diagram: {use_case_name}")

        return errors

    def _validate_relationships(self, usecase_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        actors = usecase_json.get("actors", [])
        use_cases = usecase_json.get("use_cases", [])
        relationships = usecase_json.get("relationships", [])

        actor_ids = {
            str(actor.get("id"))
            for actor in actors
            if isinstance(actor, dict) and actor.get("id")
        }

        use_case_ids = {
            str(use_case.get("id"))
            for use_case in use_cases
            if isinstance(use_case, dict) and use_case.get("id")
        }

        allowed_types = {"association", "include", "extend", "generalization"}

        for relationship in relationships:
            if not isinstance(relationship, dict):
                errors.append("Each relationship must be a JSON object.")
                continue

            source = str(relationship.get("from", "")).strip()
            target = str(relationship.get("to", "")).strip()
            relation_type = str(relationship.get("type", "")).strip()

            if not source or not target:
                errors.append("Each relationship must have from and to.")
                continue

            if relation_type not in allowed_types:
                errors.append(f"Invalid use case relationship type: {relation_type}")
                continue

            if relation_type == "association" and (source not in actor_ids or target not in use_case_ids):
                errors.append("Association relationship must be actor -> use case.")

            if relation_type == "include" and (source not in use_case_ids or target not in use_case_ids):
                errors.append("Include relationship must be base use case -> included use case.")

            if relation_type == "extend" and (source not in use_case_ids or target not in use_case_ids):
                errors.append("Extend relationship must be extension use case -> base use case.")

        return errors

    def _validate_traceability(
        self,
        srs_json: dict[str, Any],
        usecase_analysis_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        fr_ids = self._collect_ids(srs_json.get("functional_requirements", []))

        if not fr_ids:
            return errors

        covered_ids: set[str] = set()

        for use_case in usecase_json.get("use_cases", []):
            if isinstance(use_case, dict):
                covered_ids.update(map(str, use_case.get("related_requirements", []) or []))

        for relationship in usecase_json.get("relationships", []):
            if isinstance(relationship, dict):
                covered_ids.update(map(str, relationship.get("related_requirements", []) or []))

        for trace in usecase_analysis_json.get("traceability", []):
            if isinstance(trace, dict) and trace.get("source_id"):
                covered_ids.add(str(trace["source_id"]))

        missing_ids = [fr_id for fr_id in fr_ids if fr_id not in covered_ids]

        if missing_ids:
            errors.append(f"Use case diagram missing traceability for FR IDs: {missing_ids}")

        return errors

    def _validate_out_of_scope(self, srs_json: dict[str, Any], usecase_json: dict[str, Any]) -> list[str]:
        """
        Generic out-of-scope validation.

        It does not contain password/login-specific logic. It compares executable
        use case elements against SRS out_of_scope items using meaningful token
        overlap. If the SRS says "Only X is in scope", elements matching X are
        allowed while the broader forbidden item is still blocked.
        """

        errors: list[str] = []
        out_of_scope_items = srs_json.get("out_of_scope", []) or []

        if not out_of_scope_items:
            return errors

        executable_elements = self._diagram_executable_elements(usecase_json)

        for item in out_of_scope_items:
            item_text = self._item_text(item)
            forbidden_text, allowed_texts = self._split_out_of_scope_item(item_text)

            forbidden_stems = self._important_stems(forbidden_text)
            if not forbidden_stems:
                continue

            allowed_stem_sets = [self._important_stems(text) for text in allowed_texts if text]

            for element in executable_elements:
                element_text = element["text"]
                element_stems = self._important_stems(element_text)

                if not element_stems:
                    continue

                if self._matches_allowed_clause(element_stems, allowed_stem_sets):
                    continue

                overlap = forbidden_stems.intersection(element_stems)
                required_overlap = 1 if len(forbidden_stems) == 1 else 2

                if len(overlap) >= required_overlap:
                    errors.append(
                        f"Use case diagram appears to include out-of-scope item '{item_text}' in '{element_text}'."
                    )

        return errors

    # ------------------------------------------------------------------
    # Out-of-scope helper methods
    # ------------------------------------------------------------------

    def _diagram_executable_elements(self, usecase_json: dict[str, Any]) -> list[dict[str, str]]:
        elements: list[dict[str, str]] = []

        for use_case in usecase_json.get("use_cases", []):
            if isinstance(use_case, dict):
                elements.append({
                    "type": "use_case",
                    "text": f"{use_case.get('name', '')} {use_case.get('description', '')}",
                })

        for relationship in usecase_json.get("relationships", []):
            if isinstance(relationship, dict):
                label = str(relationship.get("label", "")).strip()
                if label:
                    elements.append({"type": "relationship", "text": label})

        return elements

    def _split_out_of_scope_item(self, text: str) -> tuple[str, list[str]]:
        raw = str(text)
        allowed: list[str] = []

        parenthetical_parts = re.findall(r"\(([^)]*)\)", raw)
        for part in parenthetical_parts:
            allowed.extend(self._extract_allowed_clauses(part))

        allowed.extend(self._extract_allowed_clauses(raw))

        forbidden = re.sub(r"\([^)]*\)", " ", raw)
        forbidden = re.sub(r"\bonly\b.+?\bin\s+scope\b", " ", forbidden, flags=re.IGNORECASE)
        forbidden = re.sub(r"\bexcept\b.+", " ", forbidden, flags=re.IGNORECASE)
        forbidden = re.sub(r"\ballowed\s*:\s*.+", " ", forbidden, flags=re.IGNORECASE)
        forbidden = re.sub(r"\s+", " ", forbidden).strip()

        return forbidden or raw, self._unique(allowed)

    def _extract_allowed_clauses(self, text: str) -> list[str]:
        allowed: list[str] = []

        patterns = [
            r"only\s+(.+?)\s+is\s+in\s+scope",
            r"only\s+(.+?)\s+are\s+in\s+scope",
            r"only\s+(.+?)\s+in\s+scope",
            r"except\s+(.+)$",
            r"allowed\s*:\s*(.+)$",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = match.group(1).strip(" .;:")
                if value:
                    allowed.append(value)

        return allowed

    def _matches_allowed_clause(self, element_stems: set[str], allowed_stem_sets: list[set[str]]) -> bool:
        for allowed_stems in allowed_stem_sets:
            if not allowed_stems:
                continue
            # One strong allowed token is enough for phrases such as "initiation flow".
            if element_stems.intersection(allowed_stems):
                return True
        return False

    def _important_stems(self, text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z0-9]+", str(text).lower())
        stems = set()

        for word in words:
            if word in self.STOPWORDS or len(word) < 3:
                continue
            stems.add(self._stem(word))

        return stems

    def _stem(self, word: str) -> str:
        word = word.lower()

        # Very small generic stemmer to match verify/verification and initiate/initiation.
        if word.startswith("verif"):
            return "verif"
        if word.startswith("initiat"):
            return "initiat"

        for suffix in ["ations", "ation", "itions", "ition", "ments", "ment", "ing", "ed", "es", "s"]:
            if word.endswith(suffix) and len(word) > len(suffix) + 3:
                return word[: -len(suffix)]

        return word

    # ------------------------------------------------------------------
    # General helpers
    # ------------------------------------------------------------------

    def _collect_ids(self, items: Any) -> list[str]:
        ids: list[str] = []
        if not isinstance(items, list):
            return ids
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
        return ids

    def _item_text(self, item: Any) -> str:
        if isinstance(item, dict):
            for key in ["description", "name", "title", "text", "value", "risk", "mitigation"]:
                if item.get(key):
                    return str(item[key])
            return str(item)
        return str(item)

    def _normalize(self, text: str) -> str:
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _unique(self, items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            value = str(item).strip()
            if value and value not in result:
                result.append(value)
        return result
