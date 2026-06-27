"""
Architecture Agent Use Case Validator.

Purpose:
- Validate generated UML Use Case model before PlantUML rendering.
- Keep validation feature-independent.
- Avoid false failures when the SRS out-of-scope section contains clarifying text such as:
  "Password reset via email verification (Only the initiation flow is in scope)."

Important:
This validator does not use a quality score.
It is a pass/fail rule validator.
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

    The validator checks:
    - basic structure
    - actor correctness
    - use case naming quality
    - relationship correctness
    - requirement traceability
    - out-of-scope leakage

    It intentionally avoids hardcoded feature lists such as cart/checkout/payment/signup,
    because those may be valid feature names in another iteration.
    """

    TECHNICAL_ACTOR_TERMS = [
        "database",
        "mongodb",
        "mysql",
        "postgres",
        "collection",
        "table",
        "api",
        "endpoint",
        "controller",
        "service",
        "repository",
        "model",
        "schema",
        "server",
        "backend",
        "frontend",
        "react",
        "node",
        "express",
        "mongoose",
        "jwt",
        "token",
        "library",
        "middleware",
        "component",
        "page",
        "form",
    ]

    GENERIC_USE_CASE_NAMES = [
        "use feature",
        "use system",
        "manage feature",
        "access feature",
        "perform feature",
        "do feature",
        "feature action",
    ]

    def validate(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
        usecase_analysis_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> None:
        """
        Validate final usecase_json.

        Raises:
            UseCaseValidationError if the use case model is invalid.
        """

        errors: list[str] = []

        errors.extend(self._validate_basic_structure(usecase_json))
        errors.extend(self._validate_actors(usecase_json))
        errors.extend(self._validate_use_cases(usecase_json))
        errors.extend(self._validate_relationships(usecase_json))
        errors.extend(self._validate_traceability(srs_json, usecase_analysis_json, usecase_json))
        errors.extend(self._validate_out_of_scope(srs_json, usecase_json))

        if errors:
            raise UseCaseValidationError("; ".join(errors))

    # ------------------------------------------------------------------
    # Basic structure validation
    # ------------------------------------------------------------------

    def _validate_basic_structure(self, usecase_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        if not isinstance(usecase_json, dict):
            return ["usecase_json must be a JSON object."]

        required_keys = [
            "system_boundary",
            "diagram_title",
            "actors",
            "use_cases",
            "relationships",
            "notes",
        ]

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

    # ------------------------------------------------------------------
    # Actor validation
    # ------------------------------------------------------------------

    def _validate_actors(self, usecase_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        actors = usecase_json.get("actors", [])

        seen_actor_names: set[str] = set()

        for actor in actors:
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

    # ------------------------------------------------------------------
    # Use case validation
    # ------------------------------------------------------------------

    def _validate_use_cases(self, usecase_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        use_cases = usecase_json.get("use_cases", [])

        seen_usecase_names: set[str] = set()

        for use_case in use_cases:
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

            if normalized_name in self.GENERIC_USE_CASE_NAMES:
                errors.append(f"Use case name is too generic: {use_case_name}")

            if re.fullmatch(r"use .+ feature", normalized_name):
                errors.append(f"Use case name is too generic: {use_case_name}")

            # NFRs/constraints should usually be notes, not normal use cases.
            if self._contains_any(
                normalized_name,
                ["response time", "performance", "responsive ui", "mern stack", "mvc", "architecture style"],
            ):
                errors.append(
                    f"Non-functional requirement or technical constraint used as a normal use case: {use_case_name}"
                )

        return errors

    # ------------------------------------------------------------------
    # Relationship validation
    # ------------------------------------------------------------------

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

            if relation_type == "association":
                if source not in actor_ids or target not in use_case_ids:
                    errors.append(
                        "Association relationship must be actor -> use case."
                    )

            if relation_type == "include":
                if source not in use_case_ids or target not in use_case_ids:
                    errors.append(
                        "Include relationship must be base use case -> included use case."
                    )

            if relation_type == "extend":
                if source not in use_case_ids or target not in use_case_ids:
                    errors.append(
                        "Extend relationship must be extension use case -> base use case."
                    )

        return errors

    # ------------------------------------------------------------------
    # Traceability validation
    # ------------------------------------------------------------------

    def _validate_traceability(
        self,
        srs_json: dict[str, Any],
        usecase_analysis_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> list[str]:
        """
        Ensure important functional requirements are mapped.

        This check is intentionally practical, not too strict:
        - If the main use case maps all FR IDs, it is accepted.
        - If relationships/notes map IDs, they are also accepted.
        """

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

        for note in usecase_json.get("notes", []):
            if isinstance(note, dict):
                covered_ids.update(map(str, note.get("related_requirements", []) or []))

        for trace in usecase_analysis_json.get("traceability", []):
            if isinstance(trace, dict) and trace.get("source_id"):
                covered_ids.add(str(trace["source_id"]))

        missing_ids = [fr_id for fr_id in fr_ids if fr_id not in covered_ids]

        if missing_ids:
            errors.append(f"Use case diagram missing traceability for FR IDs: {missing_ids}")

        return errors

    # ------------------------------------------------------------------
    # Out-of-scope validation
    # ------------------------------------------------------------------

    def _validate_out_of_scope(
        self,
        srs_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> list[str]:
        """
        Validate that the diagram does not include out-of-scope functionality.

        Important fix:
        We do NOT compare the full out-of-scope sentence against the full diagram JSON.
        That caused false failures for cases like:
            "Password reset via email verification (Only the initiation flow is in scope)."

        In that case, the diagram is allowed to include:
            "Initiate Forgot Password"
            "Initiate Password Recovery"
            "Initiate Password Reset Flow"

        But it must not include full reset/email verification behaviours such as:
            "Verify Email"
            "Send Reset Email"
            "Set New Password"
            "Complete Password Reset"
        """

        errors: list[str] = []
        out_of_scope_items = srs_json.get("out_of_scope", []) or []

        if not out_of_scope_items:
            return errors

        # Only validate executable diagram elements.
        # Notes are intentionally excluded because notes may quote boundaries/out-of-scope text.
        core_text = self._diagram_core_text(usecase_json)

        for item in out_of_scope_items:
            item_text = self._item_text(item)
            item_normalized = self._normalize(item_text)

            if not item_normalized:
                continue

            # Special but generic handling for "Only X is in scope" clauses.
            if "only" in item_normalized and "in scope" in item_normalized:
                errors.extend(
                    self._validate_partial_scope_clause(
                        out_of_scope_text=item_text,
                        diagram_core_text=core_text,
                    )
                )
                continue

            # For normal out-of-scope items, reject only if the actual executable
            # use case/actor/relationship text contains the out-of-scope action.
            search_phrase = self._remove_parenthetical_text(item_normalized)

            if search_phrase and search_phrase in core_text:
                errors.append(f"Use case diagram appears to include out-of-scope item: {item_text}")

        return errors

    def _validate_partial_scope_clause(
        self,
        out_of_scope_text: str,
        diagram_core_text: str,
    ) -> list[str]:
        """
        Handle out-of-scope items that also contain an allowed part.

        Example:
            Out of scope: "Password reset via email verification (Only the initiation flow is in scope)."

        Allowed:
            "Initiate Forgot Password"
            "Initiate Password Recovery"
            "Initiate Password Reset Flow"

        Not allowed:
            "Verify Email"
            "Send Reset Email"
            "Set New Password"
            "Complete Password Reset"
        """

        errors: list[str] = []
        normalized_out = self._normalize(out_of_scope_text)

        # Generic password recovery/reset boundary handling.
        if "password" in normalized_out and ("reset" in normalized_out or "recovery" in normalized_out):
            forbidden_phrases = [
                "email verification",
                "verify email",
                "verify reset email",
                "send reset email",
                "send password reset email",
                "reset email verification",
                "set new password",
                "create new password",
                "change password",
                "complete password reset",
                "complete reset",
                "confirm password reset",
            ]

            for phrase in forbidden_phrases:
                if phrase in diagram_core_text:
                    errors.append(
                        f"Use case diagram includes out-of-scope password reset/email verification behaviour: {phrase}"
                    )

            # Do not reject "password reset" by itself when the diagram clearly says initiate/initiation.
            if "password reset" in diagram_core_text:
                has_initiation_context = self._contains_any(
                    diagram_core_text,
                    [
                        "initiate password reset",
                        "initiates password reset",
                        "initiate the password reset",
                        "initiates the password reset",
                        "password reset initiation",
                        "password recovery initiation",
                        "initiate forgot password",
                        "forgot password",
                    ],
                )

                if not has_initiation_context:
                    errors.append(
                        "Use case diagram appears to include password reset beyond the initiation flow."
                    )

            return errors

        # Generic handling for other "only X is in scope" items.
        # Remove the parenthetical explanation and avoid exact whole-JSON matching.
        base_out_of_scope = self._remove_parenthetical_text(normalized_out)

        if base_out_of_scope and base_out_of_scope in diagram_core_text:
            errors.append(f"Use case diagram appears to include out-of-scope item: {out_of_scope_text}")

        return errors

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _diagram_core_text(self, usecase_json: dict[str, Any]) -> str:
        """
        Build text only from executable diagram elements.

        Excluded:
        - notes
        - standards_notes

        Why:
        Notes may intentionally mention constraints or out-of-scope boundaries.
        They should not trigger false out-of-scope errors.
        """

        parts: list[str] = []

        for actor in usecase_json.get("actors", []):
            if isinstance(actor, dict):
                parts.append(str(actor.get("name", "")))
                parts.append(str(actor.get("description", "")))

        for use_case in usecase_json.get("use_cases", []):
            if isinstance(use_case, dict):
                parts.append(str(use_case.get("name", "")))
                parts.append(str(use_case.get("description", "")))
                parts.append(" ".join(map(str, use_case.get("related_requirements", []) or [])))

        for relationship in usecase_json.get("relationships", []):
            if isinstance(relationship, dict):
                parts.append(str(relationship.get("label", "")))
                parts.append(str(relationship.get("type", "")))

        return self._normalize(" ".join(parts))

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

    def _remove_parenthetical_text(self, text: str) -> str:
        return re.sub(r"\([^)]*\)", "", text).strip()

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)
