"""
Architecture Agent SDS Validator.

Purpose:
Validate that the generated SDS follows the generic IEEE 1016-style structure
and covers the approved SRS.

This validator is feature-independent.
It does not contain Login-specific, Cart-specific, Payment-specific, or LMS-specific logic.
"""

from __future__ import annotations

from typing import Any


class SDSValidationError(Exception):
    """
    Raised when the generated SDS is incomplete or not aligned with the SRS.
    """


class ArchitectureSDSValidator:
    """
    Generic SDS validator for IEEE 1016-style feature-level SDS.
    """

    REQUIRED_TOP_LEVEL_KEYS = [
        "document_control",
        "introduction",
        "design_context",
        "design_considerations",
        "architecture_overview",
        "design_views",
        "detailed_design_decisions",
        "traceability_matrix",
        "assumptions",
        "constraints",
        "risks",
        "dependencies",
        # "use_case_diagram_reference",
        "human_approval_note",
    ]

    REQUIRED_DESIGN_VIEWS = [
        "context_view",
        "logical_view",
        "interface_view",
        "data_view",
        "behavior_view",
        "error_handling_view",
        "security_authorization_view",
        "quality_attributes_view",
    ]

    def validate(self, srs_json: dict[str, Any], sds_json: dict[str, Any]) -> None:
        """
        Validate SDS structure and SRS coverage.

        Raises:
            SDSValidationError if the SDS is incomplete.
        """

        errors: list[str] = []

        errors.extend(self._validate_required_structure(sds_json))
        errors.extend(self._validate_design_views(sds_json))
        errors.extend(self._validate_traceability_coverage(srs_json, sds_json))
        errors.extend(self._validate_interface_coverage(srs_json, sds_json))
        errors.extend(self._validate_data_coverage(srs_json, sds_json))
        errors.extend(self._validate_quality_coverage(srs_json, sds_json))
        errors.extend(self._validate_no_weak_fallback_text(sds_json))

        if errors:
            raise SDSValidationError("; ".join(errors))

    def _validate_required_structure(self, sds_json: dict[str, Any]) -> list[str]:
        errors = []

        for key in self.REQUIRED_TOP_LEVEL_KEYS:
            if key not in sds_json:
                errors.append(f"SDS missing required top-level key: {key}")

        return errors

    def _validate_design_views(self, sds_json: dict[str, Any]) -> list[str]:
        errors = []

        design_views = sds_json.get("design_views")

        if not isinstance(design_views, dict):
            return ["SDS design_views must be a JSON object."]

        for view_name in self.REQUIRED_DESIGN_VIEWS:
            if view_name not in design_views:
                errors.append(f"SDS missing required design view: {view_name}")

        return errors

    def _validate_traceability_coverage(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any]
    ) -> list[str]:
        """
        Ensure important SRS IDs are represented in traceability_matrix.
        """

        errors = []

        required_ids = []

        required_ids.extend(self._collect_ids(srs_json.get("functional_requirements", [])))
        required_ids.extend(self._collect_ids(srs_json.get("acceptance_criteria", [])))
        required_ids.extend(self._collect_ids(srs_json.get("validation_rules", [])))
        required_ids.extend(self._collect_ids(srs_json.get("non_functional_requirements", [])))

        traceability = sds_json.get("traceability_matrix", [])

        if not isinstance(traceability, list):
            return ["SDS traceability_matrix must be a list."]

        covered_ids = set()

        for item in traceability:
            if isinstance(item, dict) and item.get("source_id"):
                covered_ids.add(str(item["source_id"]))

        missing = [
            source_id
            for source_id in required_ids
            if source_id not in covered_ids
        ]

        if missing:
            errors.append(f"SDS traceability_matrix missing SRS IDs: {missing}")

        return errors

    def _validate_interface_coverage(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any]
    ) -> list[str]:
        """
        Ensure SRS API/input/output expectations are reflected in interface view.
        """

        errors = []

        interface_view = (
            sds_json
            .get("design_views", {})
            .get("interface_view", {})
        )

        api_expectations = srs_json.get("api_expectations", [])
        input_requirements = srs_json.get("input_requirements", [])
        output_requirements = srs_json.get("output_requirements", [])

        api_endpoints = interface_view.get("api_endpoints", [])
        request_models = interface_view.get("request_models", [])
        response_models = interface_view.get("response_models", [])

        if api_expectations and not api_endpoints:
            errors.append("SRS has API expectations but SDS interface_view.api_endpoints is empty.")

        if input_requirements and not request_models:
            errors.append("SRS has input requirements but SDS interface_view.request_models is empty.")

        if output_requirements and not response_models:
            errors.append("SRS has output requirements but SDS interface_view.response_models is empty.")

        expected_paths = [
            item.get("endpoint")
            for item in api_expectations
            if isinstance(item, dict) and item.get("endpoint")
        ]

        actual_paths = [
            item.get("endpoint")
            for item in api_endpoints
            if isinstance(item, dict) and item.get("endpoint")
        ]

        for path in expected_paths:
            if path not in actual_paths:
                errors.append(f"SDS interface_view missing API endpoint from SRS: {path}")

        return errors

    def _validate_data_coverage(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any]
    ) -> list[str]:
        """
        Ensure SRS data requirements are reflected in data view.
        """

        data_requirements = srs_json.get("data_requirements", [])

        if not data_requirements:
            return []

        data_view = (
            sds_json
            .get("design_views", {})
            .get("data_view", {})
        )

        data_entities = data_view.get("data_entities", [])

        if not data_entities:
            return ["SRS has data requirements but SDS data_view.data_entities is empty."]

        return []

    def _validate_quality_coverage(
        self,
        srs_json: dict[str, Any],
        sds_json: dict[str, Any]
    ) -> list[str]:
        """
        Ensure SRS NFRs are reflected in quality attributes view.
        """

        nfrs = srs_json.get("non_functional_requirements", [])

        if not nfrs:
            return []

        quality_view = (
            sds_json
            .get("design_views", {})
            .get("quality_attributes_view", {})
        )

        quality_text = str(quality_view).strip()

        if not quality_text or quality_text == "{}":
            return ["SRS has NFRs but SDS quality_attributes_view is empty."]

        return []

    def _validate_no_weak_fallback_text(self, sds_json: dict[str, Any]) -> list[str]:
        """
        Prevent approval-ready SDS from containing old generic fallback wording.
        """

        text = str(sds_json).lower()

        weak_phrases = [
            "fallback sds",
            "use existing relevant collections where possible",
            "requirement considered in fallback sds",
        ]

        return [
            f"SDS contains weak fallback phrase: {phrase}"
            for phrase in weak_phrases
            if phrase in text
        ]

    def _collect_ids(self, items: list[Any]) -> list[str]:
        ids = []

        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))

        return ids
