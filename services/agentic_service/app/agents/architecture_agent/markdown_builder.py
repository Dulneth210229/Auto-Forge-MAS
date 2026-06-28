"""
Architecture Agent SDS Markdown Builder.

Purpose:
Convert IEEE 1016-style SDS JSON into human-readable Markdown.

This builder is generic and feature-independent.
It does not contain Login-specific, Cart-specific, Payment-specific, or LMS-specific logic.
"""

from __future__ import annotations

from typing import Any


class ArchitectureSDSMarkdownBuilder:
    """
    Converts SDS JSON into SDS Markdown.
    """

    def build(self, sds_json: dict[str, Any]) -> str:
        """
        Build full IEEE 1016-style SDS Markdown document from SDS JSON.
        """

        document_control = sds_json.get("document_control", {})
        introduction = sds_json.get("introduction", {})
        design_context = sds_json.get("design_context", {})
        design_considerations = sds_json.get("design_considerations", {})
        architecture_overview = sds_json.get("architecture_overview", {})
        design_views = sds_json.get("design_views", {})

        feature_name = (
            document_control.get("feature_name")
            or sds_json.get("feature_name")
            or "Untitled Feature"
        )

        return f"""# Software Design Specification: {feature_name}

> Standard Basis: IEEE 1016-style Software Design Description  
> Artifact Type: Feature-level Software Design Specification

---

## 1. Document Control

{self._document_control(document_control)}

---

## 2. Introduction

### 2.1 Purpose
{introduction.get("purpose", "Not specified.")}

### 2.2 Scope
{self._simple_list(introduction.get("scope", []))}

### 2.3 Out of Scope
{self._simple_list(introduction.get("out_of_scope", []))}

### 2.4 Intended Audience
{self._simple_list(introduction.get("intended_audience", []))}

### 2.5 Definitions
{self._definition_list(introduction.get("definitions", []))}

---

## 3. Design Context

### 3.1 Business Goal
{design_context.get("business_goal", "Not specified.")}

### 3.2 User Roles
{self._simple_list(design_context.get("user_roles", []))}

### 3.3 Feature Boundary
{design_context.get("feature_boundary", "Not specified.")}

### 3.4 Operating Environment
{design_context.get("operating_environment", "Not specified.")}

### 3.5 Dependencies
{self._simple_list(design_context.get("dependencies", []))}

### 3.6 Assumptions
{self._simple_list(design_context.get("assumptions", []))}

---

## 4. Design Considerations

### 4.1 Constraints
{self._simple_list(design_considerations.get("constraints", []))}

### 4.2 Non-Functional Requirements
{self._records_list(design_considerations.get("non_functional_requirements", []))}

### 4.3 Risks
{self._records_list(design_considerations.get("risks", []))}

### 4.4 Design Trade-offs
{self._simple_list(design_considerations.get("design_tradeoffs", []))}

---

## 5. Architecture Overview

### 5.1 Architecture Style
{architecture_overview.get("architecture_style", "Not specified.")}

### 5.2 Architecture Rationale
{architecture_overview.get("architecture_rationale", "Not specified.")}

### 5.3 Frontend Overview
{architecture_overview.get("frontend_overview", "Not specified.")}

### 5.4 Backend Overview
{architecture_overview.get("backend_overview", "Not specified.")}

### 5.5 Data Overview
{architecture_overview.get("data_overview", "Not specified.")}

### 5.6 Integration Overview
{architecture_overview.get("integration_overview", "Not specified.")}

---

## 6. Feature-Level Design Views

### 6.1 Context View
{self._context_view(design_views.get("context_view", {}))}

### 6.2 Logical View
{self._logical_view(design_views.get("logical_view", {}))}

### 6.3 Interface View
{self._interface_view(design_views.get("interface_view", {}))}

### 6.4 Data View
{self._data_view(design_views.get("data_view", {}))}

### 6.5 Interaction / Behavior View
{self._behavior_view(design_views.get("behavior_view", {}))}

### 6.6 Error Handling View
{self._error_handling_view(design_views.get("error_handling_view", {}))}

### 6.7 Security and Authorization View
{self._security_view(design_views.get("security_authorization_view", {}))}

### 6.8 Quality Attributes View
{self._quality_view(design_views.get("quality_attributes_view", {}))}

---

## 7. Detailed Design Decisions

{self._design_decisions(sds_json.get("detailed_design_decisions", []))}

---

## 8. Requirement-to-Design Traceability Matrix

{self._traceability_matrix(sds_json.get("traceability_matrix", []))}

---

## 9. Assumptions, Constraints, Risks, and Dependencies

### 9.1 Assumptions
{self._simple_list(sds_json.get("assumptions", []))}

### 9.2 Constraints
{self._simple_list(sds_json.get("constraints", []))}

### 9.3 Risks
{self._records_list(sds_json.get("risks", []))}

### 9.4 Dependencies
{self._simple_list(sds_json.get("dependencies", []))}

---

## 10. Use Case Diagram Reference

{self._usecase_reference(sds_json.get("use_case_diagram_reference", {}))}

---

## 11. Human Approval Note

{sds_json.get("human_approval_note", "This SDS must be reviewed and approved before the UI/UX Agent starts.")}
"""

    def _document_control(self, data: dict[str, Any]) -> str:
        rows = [
            ("Document Title", data.get("document_title", "N/A")),
            ("Document Type", data.get("document_type", "Software Design Specification")),
            ("Standard Basis", data.get("standard_basis", "IEEE 1016-style Software Design Description")),
            ("Project ID", data.get("project_id", "N/A")),
            ("Project Name", data.get("project_name", "N/A")),
            ("Project Type", data.get("project_type", "N/A")),
            ("Feature ID", data.get("feature_id", "N/A")),
            ("Feature Name", data.get("feature_name", "N/A")),
            ("Target Stack", data.get("target_stack", "N/A")),
            ("Architecture Style", data.get("architecture_style", "N/A")),
            ("Version", data.get("version", "v1")),
            ("Generated By", data.get("generated_by", "Architecture Agent")),
            ("Approval Status", data.get("approval_status", "pending")),
        ]

        lines = ["| Field | Value |", "|---|---|"]

        for key, value in rows:
            lines.append(f"| {key} | {self._inline(value)} |")

        input_artifacts = data.get("input_artifacts", [])
        lines.append(f"| Input Artifacts | {self._inline(', '.join(map(str, input_artifacts)) if input_artifacts else 'N/A')} |")

        return "\n".join(lines)

    def _context_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            f"**Feature Boundary:** {data.get('feature_boundary', 'Not specified.')}",
            "",
            "**Actors:**",
            self._simple_list(data.get("actors", [])),
            "",
            "**External Systems:**",
            self._simple_list(data.get("external_systems", [])),
            "",
            "**Main Interactions:**",
            self._simple_list(data.get("main_interactions", [])),
        ])

    def _logical_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**Frontend Modules:**",
            self._records_list(data.get("frontend_modules", [])),
            "",
            "**Backend Modules:**",
            self._records_list(data.get("backend_modules", [])),
            "",
            "**Domain Services:**",
            self._records_list(data.get("domain_services", [])),
            "",
            "**Data Modules:**",
            self._records_list(data.get("data_modules", [])),
            "",
            "**Integration Points:**",
            self._records_list(data.get("integration_points", [])),
        ])

    def _interface_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**API Endpoints:**",
            self._api_endpoints(data.get("api_endpoints", [])),
            "",
            "**Request Models:**",
            self._models(data.get("request_models", [])),
            "",
            "**Response Models:**",
            self._models(data.get("response_models", [])),
            "",
            "> Note: This is only an SDS-level interface design summary. The Architecture Agent is not generating a separate API contract artifact.",
        ])

    def _data_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**Data Entities:**",
            self._data_entities(data.get("data_entities", [])),
            "",
            "**Storage Rules:**",
            self._simple_list(data.get("storage_rules", [])),
            "",
            "**Data Validation Rules:**",
            self._records_list(data.get("data_validation_rules", [])),
        ])

    def _behavior_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**Main Success Flow:**",
            self._simple_list(data.get("main_success_flow", [])),
            "",
            "**Alternative Flows:**",
            self._records_list(data.get("alternative_flows", [])),
            "",
            "**Exception Flows:**",
            self._records_list(data.get("exception_flows", [])),
            "",
            "**State Changes:**",
            self._records_list(data.get("state_changes", [])),
        ])

    def _error_handling_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**Validation Errors:**",
            self._records_list(data.get("validation_errors", [])),
            "",
            "**Business Errors:**",
            self._records_list(data.get("business_errors", [])),
            "",
            "**Authorization Errors:**",
            self._records_list(data.get("authorization_errors", [])),
            "",
            "**System Errors:**",
            self._records_list(data.get("system_errors", [])),
            "",
            "**User Message Rules:**",
            self._simple_list(data.get("user_message_rules", [])),
        ])

    def _security_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**Authentication Design:**",
            self._records_list(data.get("authentication_design", [])),
            "",
            "**Authorization Design:**",
            self._records_list(data.get("authorization_design", [])),
            "",
            "**Sensitive Data Rules:**",
            self._records_list(data.get("sensitive_data_rules", [])),
            "",
            "**Risk Mitigations:**",
            self._records_list(data.get("risk_mitigations", [])),
        ])

    def _quality_view(self, data: dict[str, Any]) -> str:
        sections = []

        for key, title in [
            ("performance", "Performance"),
            ("usability", "Usability"),
            ("reliability", "Reliability"),
            ("scalability", "Scalability"),
            ("maintainability", "Maintainability"),
            ("accessibility", "Accessibility"),
        ]:
            sections.append(f"**{title}:**")
            sections.append(self._records_list(data.get(key, [])))
            sections.append("")

        return "\n".join(sections).strip()

    def _api_endpoints(self, endpoints: list[Any]) -> str:
        if not endpoints:
            return "- Not specified."

        lines = []

        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                lines.append(f"- {endpoint}")
                continue

            method = endpoint.get("method", "METHOD")
            path = endpoint.get("endpoint", "/path")
            purpose = endpoint.get("purpose", "No purpose provided.")
            request_model = endpoint.get("request_model", "N/A")
            success_model = endpoint.get("success_response_model", "N/A")
            error_model = endpoint.get("error_response_model", "N/A")
            related = endpoint.get("related_requirements", [])

            lines.append(f"- **{method} {path}**")
            lines.append(f"  - Purpose: {purpose}")
            lines.append(f"  - Request Model: {request_model}")
            lines.append(f"  - Success Response Model: {success_model}")
            lines.append(f"  - Error Response Model: {error_model}")
            lines.append(f"  - Related Requirements: {self._join(related)}")

        return "\n".join(lines)

    def _models(self, models: list[Any]) -> str:
        if not models:
            return "- Not specified."

        lines = []

        for model in models:
            if not isinstance(model, dict):
                lines.append(f"- {model}")
                continue

            lines.append(f"- **{model.get('name', 'Model')}**")
            if model.get("type"):
                lines.append(f"  - Type: {model.get('type')}")
            lines.append("  - Fields:")

            fields = model.get("fields", [])

            if fields:
                for field in fields:
                    lines.append(f"    - {self._inline(field)}")
            else:
                lines.append("    - Not specified.")

            lines.append(f"  - Related Requirements: {self._join(model.get('related_requirements', []))}")

        return "\n".join(lines)

    def _data_entities(self, entities: list[Any]) -> str:
        if not entities:
            return "- Not specified."

        lines = []

        for entity in entities:
            if not isinstance(entity, dict):
                lines.append(f"- {entity}")
                continue

            lines.append(f"- **{entity.get('name', 'Entity')}**")
            lines.append(f"  - Purpose: {entity.get('purpose', 'Not specified.')}")
            lines.append("  - Fields:")
            for field in entity.get("fields", []) or ["Not specified."]:
                lines.append(f"    - {self._inline(field)}")

            lines.append("  - Relationships:")
            for relationship in entity.get("relationships", []) or ["Not specified."]:
                lines.append(f"    - {self._inline(relationship)}")

            lines.append("  - Indexes / Constraints:")
            for constraint in entity.get("indexes_or_constraints", []) or ["Not specified."]:
                lines.append(f"    - {self._inline(constraint)}")

            lines.append(f"  - Related Requirements: {self._join(entity.get('related_requirements', []))}")

        return "\n".join(lines)

    def _design_decisions(self, decisions: list[Any]) -> str:
        if not decisions:
            return "- Not specified."

        lines = []

        for decision in decisions:
            if not isinstance(decision, dict):
                lines.append(f"- {decision}")
                continue

            lines.append(f"- **{decision.get('decision_id', 'DEC')}**: {decision.get('decision', 'Not specified.')}")
            lines.append(f"  - Rationale: {decision.get('rationale', 'Not specified.')}")
            lines.append(f"  - Related Requirements: {self._join(decision.get('related_requirements', []))}")

        return "\n".join(lines)

    def _traceability_matrix(self, items: list[Any]) -> str:
        if not items:
            return "- Not specified."

        lines = [
            "| Source ID | Source Type | SDS Section | Design Element | Coverage |",
            "|---|---|---|---|---|",
        ]

        for item in items:
            if not isinstance(item, dict):
                continue

            lines.append(
                f"| {item.get('source_id', 'N/A')} "
                f"| {item.get('source_type', 'N/A')} "
                f"| {item.get('sds_section', 'N/A')} "
                f"| {item.get('design_element', 'N/A')} "
                f"| {item.get('coverage_status', 'covered')} |"
            )

        return "\n".join(lines)

    def _usecase_reference(self, data: dict[str, Any]) -> str:
        if not data:
            return "- Not specified."

        lines = [
            f"- **PUML File:** {data.get('puml_file', 'Generated separately')}",
            f"- **PNG File:** {data.get('png_file', 'Generated separately')}",
            f"- **Diagram Scope:** {data.get('diagram_scope', 'Feature-level use case diagram')}",
            f"- **Actors:** {self._join(data.get('actors', []))}",
            f"- **Main Use Cases:** {self._join(data.get('main_use_cases', []))}",
            "- **Relationship Summary:**",
            self._simple_list(data.get("relationship_summary", [])),
        ]

        return "\n".join(lines)

    def _definition_list(self, items: list[Any]) -> str:
        if not items:
            return "- Not specified."

        lines = []

        for item in items:
            if isinstance(item, dict):
                term = item.get("term", "Term")
                definition = item.get("definition", "Not specified.")
                lines.append(f"- **{term}:** {definition}")
            else:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def _records_list(self, items: list[Any]) -> str:
        if not items:
            return "- Not specified."

        lines = []

        for item in items:
            if isinstance(item, dict):
                lines.append(f"- {self._inline(item)}")
            else:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def _simple_list(self, items: list[Any]) -> str:
        if not items:
            return "- Not specified."

        return "\n".join(f"- {self._inline(item)}" for item in items)

    def _join(self, items: Any) -> str:
        if not items:
            return "N/A"

        if isinstance(items, list):
            return ", ".join(str(item) for item in items)

        return str(items)

    def _inline(self, value: Any) -> str:
        if isinstance(value, dict):
            return ", ".join(f"{key}: {val}" for key, val in value.items())

        if isinstance(value, list):
            return ", ".join(str(item) for item in value)

        return str(value)
