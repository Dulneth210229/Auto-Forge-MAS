"""
Architecture Agent Use Case Validator.

Purpose:
This validator checks whether the generated use case model is good enough
before converting it into PlantUML.

Why this is needed:
LLMs sometimes generate diagrams that are technically valid but too simple.

Example of weak output:
    Customer -> Use Login Feature

This validator prevents that by checking:
- actors
- use cases
- relationships
- traceability
- include/extend usage
- feature scope
"""

from typing import Any


class UseCaseValidationError(Exception):
    """
    Raised when the generated use case model is too weak or invalid.
    """


class UseCaseQualityValidator:
    """
    Validates usecase_analysis_json and usecase_json.
    """

    TECHNICAL_ACTOR_WORDS = [
        "database",
        "mongodb",
        "api",
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
    ]

    UNRELATED_FEATURE_WORDS = [
        "cart",
        "checkout",
        "payment",
        "product listing",
        "order management",
        "wishlist",
        "inventory",
        "signup",
        "registration",
    ]

    GENERIC_USE_CASE_NAMES = [
        "use feature",
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
        Main validation method.

        Raises:
            UseCaseValidationError if the diagram is not acceptable.
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
        Validate required top-level use case diagram fields.
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

        return errors

    def _validate_actors(self, usecase_json: dict[str, Any]) -> list[str]:
        """
        Validate that actors are real user roles, not technical components.
        """

        errors = []

        for actor in usecase_json.get("actors", []):
            actor_name = str(actor.get("name", "")).lower()

            if not actor.get("id") or not actor.get("name"):
                errors.append("Each actor must have id and name.")

            for technical_word in self.TECHNICAL_ACTOR_WORDS:
                if technical_word in actor_name:
                    errors.append(
                        f"Invalid actor '{actor.get('name')}'. "
                        "Actors must be external roles, not technical components."
                    )

        return errors

    def _validate_use_cases(self, usecase_json: dict[str, Any]) -> list[str]:
        """
        Validate use case names and IDs.
        """

        errors = []

        for use_case in usecase_json.get("use_cases", []):
            use_case_name = str(use_case.get("name", "")).lower()

            if not use_case.get("id") or not use_case.get("name"):
                errors.append("Each use case must have id and name.")

            if use_case_name in self.GENERIC_USE_CASE_NAMES:
                errors.append(
                    f"Generic use case name found: '{use_case.get('name')}'. "
                    "Use case must be a real user/system behaviour."
                )

        return errors

    def _validate_relationships(self, usecase_json: dict[str, Any]) -> list[str]:
        """
        Validate relationships.

        A meaningful use case diagram should have relationships.
        """

        errors = []

        relationships = usecase_json.get("relationships", [])

        if not isinstance(relationships, list) or not relationships:
            errors.append("Use case diagram must have relationships.")
            return errors

        valid_types = ["association", "include", "extend", "generalization"]

        for relationship in relationships:
            if relationship.get("type") not in valid_types:
                errors.append(
                    f"Invalid relationship type: {relationship.get('type')}"
                )

            if not relationship.get("from") or not relationship.get("to"):
                errors.append("Each relationship must have from and to.")

        return errors

    def _validate_traceability(
        self,
        srs_json: dict[str, Any],
        usecase_json: dict[str, Any],
        usecase_analysis_json: dict[str, Any],
    ) -> list[str]:
        """
        Validate that important requirements are mapped.

        We especially check functional requirements because use case diagrams
        should reflect user-visible functional behaviour.
        """

        errors = []

        functional_requirement_ids = self._collect_ids(
            srs_json.get("functional_requirements", [])
        )

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

        missing = [
            requirement_id
            for requirement_id in functional_requirement_ids
            if requirement_id not in mapped_ids
        ]

        if missing:
            errors.append(
                f"Use case diagram does not map these functional requirements: {missing}"
            )

        return errors

    def _validate_feature_scope(
        self,
        srs_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> list[str]:
        """
        Prevent unrelated feature use cases.

        Example:
        Login diagram should not include cart, checkout, payment, etc.
        """

        errors = []

        feature_name = str(srs_json.get("feature_name", "")).lower()

        all_text = str(usecase_json).lower()

        for unrelated_word in self.UNRELATED_FEATURE_WORDS:
            if unrelated_word == feature_name:
                continue

            if unrelated_word in all_text:
                errors.append(
                    f"Use case diagram includes unrelated feature: {unrelated_word}"
                )

        return errors

    def _validate_quality_depth(
        self,
        srs_json: dict[str, Any],
        usecase_json: dict[str, Any],
    ) -> list[str]:
        """
        Check diagram quality depth.

        If SRS has multiple functional requirements and acceptance criteria,
        but the diagram has only one use case and no include/extend,
        then it is too shallow.
        """

        errors = []

        use_cases = usecase_json.get("use_cases", [])
        relationships = usecase_json.get("relationships", [])

        has_include = any(
            relation.get("type") == "include"
            for relation in relationships
        )

        has_extend = any(
            relation.get("type") == "extend"
            for relation in relationships
        )

        functional_count = len(srs_json.get("functional_requirements", []))
        acceptance_count = len(srs_json.get("acceptance_criteria", []))
        validation_count = len(srs_json.get("validation_rules", []))

        srs_has_depth = functional_count > 1 or acceptance_count > 1 or validation_count > 0

        if srs_has_depth and len(use_cases) <= 1:
            errors.append(
                "Use case diagram is too simple for this SRS. "
                "It must include main, included, extension, validation, or note elements."
            )

        if srs_has_depth and not has_include and not has_extend:
            errors.append(
                "Use case diagram must include at least one <<include>> or <<extend>> relationship "
                "when SRS contains validation, success, alternative, or error flows."
            )

        return errors

    def _collect_ids(self, items: list[Any]) -> list[str]:
        """
        Collect IDs from list of requirement-like dictionaries.
        """

        ids = []

        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(item["id"])

        return ids