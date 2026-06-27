"""
Architecture Agent Use Case Validator.

Purpose:
Validate the generated UML use case model before converting it into PlantUML.

Important:
This validator is intentionally rule-based, not score-based. It does not use a
quality_score.py file. It simply accepts or rejects the use case model using
feature-independent UML rules.
"""

from __future__ import annotations

from typing import Any


class UseCaseValidationError(Exception):
    """
    Raised when the generated use case model is invalid or too weak.
    """


class UseCaseQualityValidator:
    """
    Validates usecase_analysis_json and usecase_json.
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
        "use login feature",
        "manage feature",
        "access feature",
        "perform feature",
    ]

    def validate(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any],
        usecase_analysis_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> None:
        """
        Validate the final use case model.
        """

        errors: list[str] = []

        errors.extend(self._validate_basic_structure(usecase_json))
        errors.extend(self._validate_actors(usecase_json))
        errors.extend(self._validate_use_cases(usecase_json))
        errors.extend(self._validate_relationships(usecase_json))
        errors.extend(self._validate_traceability(srs_json, usecase_json, usecase_analysis_json))
        errors.extend(self._validate_feature_scope(srs_json, usecase_json))
        errors.extend(self._validate_quality_depth(srs_json, usecase_json))

        if errors:
            raise UseCaseValidationError("; ".join(errors))

    def _validate_basic_structure(self, usecase_json: dict[str, Any]) -> list[str]:
        """
        Validate required use case model fields.
        """

        errors = []

        if not usecase_json.get("system_boundary"):
            errors.append("Use case diagram must have a system boundary.")

        if not usecase_json.get("diagram_title"):
            errors.append("Use case diagram must have a diagram title.")

        if not isinstance(usecase_json.get("actors"), list) or not usecase_json.get("actors"):
            errors.append("Use case diagram must have at least one actor.")

        if not isinstance(usecase_json.get("use_cases"), list) or not usecase_json.get("use_cases"):
            errors.append("Use case diagram must have at least one use case.")

        if not isinstance(usecase_json.get("relationships"), list) or not usecase_json.get("relationships"):
            errors.append("Use case diagram must have relationships.")

        if not isinstance(usecase_json.get("notes", []), list):
            errors.append("Use case diagram notes must be a list.")

        return errors

    def _validate_actors(self, usecase_json: dict[str, Any]) -> list[str]:
        """
        Validate actors are external roles/systems, not implementation components.
        """

        errors = []

        for actor in usecase_json.get("actors", []):
            actor_name = str(actor.get("name", "")).strip()
            actor_name_lower = actor_name.lower()

            if not actor.get("id") or not actor_name:
                errors.append("Each actor must have id and name.")

            for technical_word in self.TECHNICAL_ACTOR_WORDS:
                if technical_word in actor_name_lower:
                    errors.append(
                        f"Invalid actor '{actor_name}'. Actors must be external roles or external systems, not technical components."
                    )

        return errors

    def _validate_use_cases(self, usecase_json: dict[str, Any]) -> list[str]:
        """
        Validate use case names and categories.
        """

        errors = []
        valid_categories = {"main", "included", "extension", "supporting"}

        for use_case in usecase_json.get("use_cases", []):
            use_case_name = str(use_case.get("name", "")).strip()
            use_case_name_lower = use_case_name.lower()

            if not use_case.get("id") or not use_case_name:
                errors.append("Each use case must have id and name.")

            if use_case_name_lower in self.GENERIC_USE_CASE_NAMES:
                errors.append(
                    f"Generic use case name found: '{use_case_name}'. Use case must be a real goal/action."
                )

            category = use_case.get("category")
            if category and category not in valid_categories:
                errors.append(f"Invalid use case category: {category}")

        return errors

    def _validate_relationships(self, usecase_json: dict[str, Any]) -> list[str]:
        """
        Validate relationships and include/extend direction.
        """

        errors = []
        valid_types = {"association", "include", "extend", "generalization"}

        use_case_ids = {item.get("id") for item in usecase_json.get("use_cases", [])}
        actor_ids = {item.get("id") for item in usecase_json.get("actors", [])}

        for relationship in usecase_json.get("relationships", []):
            source = relationship.get("from")
            target = relationship.get("to")
            relation_type = relationship.get("type")

            if relation_type not in valid_types:
                errors.append(f"Invalid relationship type: {relation_type}")

            if not source or not target:
                errors.append("Each relationship must have from and to.")
                continue

            if relation_type == "association":
                if source not in actor_ids or target not in use_case_ids:
                    errors.append("Association must go from actor to use case.")

            if relation_type == "include":
                if source not in use_case_ids or target not in use_case_ids:
                    errors.append("Include relationship must connect use case to use case.")

            if relation_type == "extend":
                if source not in use_case_ids or target not in use_case_ids:
                    errors.append("Extend relationship must connect use case to use case.")

        return errors

    def _validate_traceability(
        self,
        srs_json: dict[str, Any],
        usecase_json: dict[str, Any],
        usecase_analysis_json: dict[str, Any],
    ) -> list[str]:
        """
        Validate that all functional requirements are represented.
        """

        errors = []

        functional_requirement_ids = self._collect_ids(srs_json.get("functional_requirements", []))
        if not functional_requirement_ids:
            return errors

        mapped_ids = set()

        for use_case in usecase_json.get("use_cases", []):
            mapped_ids.update(use_case.get("related_requirements", []))

        for relationship in usecase_json.get("relationships", []):
            mapped_ids.update(relationship.get("related_requirements", []))

        for note in usecase_json.get("notes", []):
            mapped_ids.update(note.get("related_requirements", []))

        for trace in usecase_analysis_json.get("traceability", []):
            source_id = trace.get("source_id")
            if source_id:
                mapped_ids.add(source_id)

        missing = [req_id for req_id in functional_requirement_ids if req_id not in mapped_ids]

        if missing:
            errors.append(f"Use case diagram does not map these functional requirements: {missing}")

        return errors

    def _validate_feature_scope(
        self,
        srs_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> list[str]:
        """
        Prevent out-of-scope SRS items appearing as use cases.

        This replaces the earlier hardcoded unrelated feature list. It is generic
        and works for Login, Cart, Checkout, LMS, and future features.
        """

        errors = []
        all_text = str(usecase_json).lower()

        out_of_scope_items = srs_json.get("out_of_scope", [])
        if not isinstance(out_of_scope_items, list):
            out_of_scope_items = [out_of_scope_items]

        for item in out_of_scope_items:
            item_text = self._extract_text(item).lower()
            if not item_text:
                continue

            # Do not fail on tiny/common words. Check meaningful phrases only.
            important_terms = [term for term in item_text.replace("(", " ").replace(")", " ").split() if len(term) >= 5]
            matched_terms = [term for term in important_terms if term in all_text]

            if len(matched_terms) >= 2:
                errors.append(f"Use case diagram appears to include out-of-scope item: {item_text}")

        return errors

    def _validate_quality_depth(
        self,
        srs_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> list[str]:
        """
        Check that the diagram is not too shallow for the SRS.
        """

        errors = []

        use_cases = usecase_json.get("use_cases", [])
        relationships = usecase_json.get("relationships", [])

        has_include = any(relation.get("type") == "include" for relation in relationships)
        has_extend = any(relation.get("type") == "extend" for relation in relationships)

        functional_count = len(srs_json.get("functional_requirements", []))
        acceptance_count = len(srs_json.get("acceptance_criteria", []))
        validation_count = len(srs_json.get("validation_rules", []))

        srs_has_depth = functional_count > 1 or acceptance_count > 1 or validation_count > 0

        if srs_has_depth and len(use_cases) <= 1:
            errors.append(
                "Use case diagram is too simple for this SRS. It must include main, included, extension, validation, or note elements."
            )

        if validation_count > 0 and not has_include:
            errors.append("Use case diagram should include mandatory validation behaviour using <<include>> when SRS has validation rules.")

        if acceptance_count > 1 and not has_include and not has_extend:
            errors.append("Use case diagram should include <<include>> or <<extend>> relationships when SRS has multiple scenarios.")

        return errors

    def _collect_ids(self, items: list[Any]) -> list[str]:
        ids = []
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(item["id"])
        return ids

    def _extract_text(self, item: Any) -> str:
        if isinstance(item, dict):
            return str(
                item.get("description")
                or item.get("name")
                or item.get("risk")
                or item.get("expectation")
                or item.get("payload")
                or item
            )
        return str(item)
