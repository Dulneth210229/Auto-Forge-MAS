"""
Architecture Agent Class Diagram Modeler.

Purpose:
Build a standard UML Class Diagram model from approved SRS and SDS data.

Design principle:
- Feature-independent.
- Does not hardcode Login, Cart, Payment, LMS, or any specific feature.
- Builds classes from SDS logical, interface, and data views.
- Shows structure only, not behaviour flow.

UML class rules applied:
- Classes represent structural design elements: boundary/control/service/repository/entity/DTO/external provider.
- Attributes are fields from request/response/data models.
- Operations are derived from API endpoints and functional responsibilities.
- Relationships show dependency/association between design classes.
- NFRs, risks, constraints, and use case names are not created as classes.
"""

from __future__ import annotations

import re
from typing import Any


class ArchitectureClassModeler:
    """
    Builds class_diagram_json from SRS and SDS.
    """

    COMMON_FIELDS = {
        "email": ("email", "String"),
        "password": ("password", "String"),
        "hashed password": ("passwordHash", "String"),
        "hash": ("passwordHash", "String"),
        "token": ("token", "String"),
        "jwt": ("token", "String"),
        "role": ("role", "String"),
        "status": ("status", "String"),
        "name": ("name", "String"),
        "username": ("username", "String"),
        "price": ("price", "Number"),
        "amount": ("amount", "Number"),
        "quantity": ("quantity", "Number"),
        "date": ("date", "Date"),
    }

    def build(self, srs_json: dict[str, Any], sds_json: dict[str, Any]) -> dict[str, Any]:
        feature_name = self._feature_name(srs_json, sds_json)
        feature_pascal = self._pascal(feature_name)
        design_views = sds_json.get("design_views", {}) if isinstance(sds_json, dict) else {}
        interface_view = design_views.get("interface_view", {}) if isinstance(design_views, dict) else {}
        data_view = design_views.get("data_view", {}) if isinstance(design_views, dict) else {}

        api_endpoints = self._as_list(interface_view.get("api_endpoints"))
        request_models = self._as_list(interface_view.get("request_models"))
        response_models = self._as_list(interface_view.get("response_models"))
        data_entities = self._as_list(data_view.get("data_entities"))
        functional_requirements = self._as_list(srs_json.get("functional_requirements"))
        data_requirements = self._as_list(srs_json.get("data_requirements"))
        output_requirements = self._as_list(srs_json.get("output_requirements"))
        validation_rules = self._as_list(srs_json.get("validation_rules"))

        classes: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        controller_id = "CLS_CONTROLLER"
        service_id = "CLS_SERVICE"
        repository_id = "CLS_REPOSITORY"

        classes.append({
            "id": controller_id,
            "name": f"{feature_pascal}Controller",
            "stereotype": "control",
            "attributes": [],
            "operations": self._controller_operations(api_endpoints, feature_name),
            "related_requirements": self._ids(functional_requirements),
        })

        classes.append({
            "id": service_id,
            "name": f"{feature_pascal}Service",
            "stereotype": "service",
            "attributes": [],
            "operations": self._service_operations(functional_requirements, feature_name),
            "related_requirements": self._ids(functional_requirements),
        })

        relationships.append({
            "from": controller_id,
            "to": service_id,
            "type": "dependency",
            "label": "uses",
        })

        dto_class_ids = []
        for index, model in enumerate(request_models, start=1):
            class_id = f"CLS_REQUEST_{index:03d}"
            dto_class_ids.append(class_id)
            classes.append({
                "id": class_id,
                "name": self._safe_class_name(self._extract_name(model) or f"{feature_pascal}Request"),
                "stereotype": "dto",
                "attributes": self._fields_from_model(model),
                "operations": [],
                "related_requirements": self._related(model, self._ids(validation_rules) + self._ids(functional_requirements)),
            })
            relationships.append({
                "from": controller_id,
                "to": class_id,
                "type": "dependency",
                "label": "accepts",
            })

        for index, model in enumerate(response_models, start=1):
            class_id = f"CLS_RESPONSE_{index:03d}"
            dto_class_ids.append(class_id)
            classes.append({
                "id": class_id,
                "name": self._safe_class_name(self._extract_name(model) or f"{feature_pascal}Response"),
                "stereotype": "dto",
                "attributes": self._fields_from_model(model) or self._fields_from_requirements(output_requirements),
                "operations": [],
                "related_requirements": self._related(model, self._ids(output_requirements)),
            })
            relationships.append({
                "from": controller_id,
                "to": class_id,
                "type": "dependency",
                "label": "returns",
            })

        entity_ids = []
        for index, entity in enumerate(data_entities or data_requirements, start=1):
            class_id = f"CLS_ENTITY_{index:03d}"
            entity_ids.append(class_id)
            entity_name = self._extract_name(entity) or f"{feature_pascal}Data"
            entity_text = self._text(entity)
            classes.append({
                "id": class_id,
                "name": self._safe_class_name(entity_name),
                "stereotype": "entity",
                "attributes": self._fields_from_entity(entity) or self._infer_fields_from_text(entity_text),
                "operations": [],
                "related_requirements": self._related(entity, self._ids(data_requirements) + self._ids(functional_requirements)),
            })

        if entity_ids:
            classes.append({
                "id": repository_id,
                "name": f"{feature_pascal}Repository",
                "stereotype": "repository",
                "attributes": [],
                "operations": [
                    {"name": "findRequiredData", "parameters": [], "return_type": "Entity", "visibility": "+"},
                    {"name": "saveChanges", "parameters": [], "return_type": "void", "visibility": "+"},
                ],
                "related_requirements": self._ids(data_requirements) + self._ids(functional_requirements),
            })
            relationships.append({
                "from": service_id,
                "to": repository_id,
                "type": "dependency",
                "label": "uses",
            })
            for entity_id in entity_ids:
                relationships.append({
                    "from": repository_id,
                    "to": entity_id,
                    "type": "association",
                    "label": "manages",
                })

        if self._needs_security_provider(srs_json):
            provider_id = "CLS_EXTERNAL_SECURITY"
            classes.append({
                "id": provider_id,
                "name": "SecurityTokenProvider",
                "stereotype": "external",
                "attributes": [],
                "operations": [
                    {"name": "generateToken", "parameters": ["payload"], "return_type": "String", "visibility": "+"}
                ],
                "related_requirements": self._ids([item for item in functional_requirements if self._has_any(self._text(item), ["jwt", "token", "generate"])]),
            })
            relationships.append({
                "from": service_id,
                "to": provider_id,
                "type": "dependency",
                "label": "generates",
            })

        classes = self._dedupe_classes(classes)
        relationships = self._filter_relationships(relationships, classes)

        return {
            "diagram_title": f"{feature_name} Class Diagram",
            "feature_name": feature_name,
            "classes": classes,
            "relationships": relationships,
            "traceability": self._build_traceability(classes, relationships),
            "rules_applied": [
                "Classes are derived from SDS interface, logical, and data views.",
                "DTO classes come from request and response models.",
                "Entity classes come from SDS data entities or SRS data requirements.",
                "Controller, service, and repository classes represent feature-level MVC/design responsibilities.",
                "NFRs, risks, constraints, and architecture notes are not generated as classes.",
            ],
        }

    # ------------------------------------------------------------------
    # Class construction helpers
    # ------------------------------------------------------------------

    def _controller_operations(self, endpoints: list[Any], feature_name: str) -> list[dict[str, Any]]:
        operations: list[dict[str, Any]] = []
        if not endpoints:
            return [{"name": self._operation_name(f"handle {feature_name}"), "parameters": ["request"], "return_type": "Response", "visibility": "+"}]

        for endpoint in endpoints:
            method = str(endpoint.get("method", "handle") if isinstance(endpoint, dict) else "handle")
            path = str(endpoint.get("endpoint", feature_name) if isinstance(endpoint, dict) else feature_name)
            operations.append({
                "name": self._operation_name(f"{method} {path}"),
                "parameters": ["request"],
                "return_type": "Response",
                "visibility": "+",
            })
        return operations

    def _service_operations(self, requirements: list[Any], feature_name: str) -> list[dict[str, Any]]:
        operations: list[dict[str, Any]] = []
        for item in requirements:
            text = self._text(item)
            name = self._operation_from_requirement(text)
            if name:
                operations.append({
                    "name": name,
                    "parameters": ["input"],
                    "return_type": "Result",
                    "visibility": "+",
                })
        if not operations:
            operations.append({"name": self._operation_name(f"process {feature_name}"), "parameters": ["input"], "return_type": "Result", "visibility": "+"})
        return self._dedupe_operations(operations)

    def _fields_from_model(self, model: Any) -> list[dict[str, Any]]:
        if not isinstance(model, dict):
            return []
        fields: list[dict[str, Any]] = []
        for field in self._as_list(model.get("fields")):
            fields.append(self._field_record(field))
        return self._dedupe_fields(fields)

    def _fields_from_entity(self, entity: Any) -> list[dict[str, Any]]:
        if not isinstance(entity, dict):
            return []
        fields: list[dict[str, Any]] = []
        for field in self._as_list(entity.get("fields")):
            record = self._field_record(field)
            if not self._looks_like_bad_inferred_field(record["name"]):
                fields.append(record)
        return self._dedupe_fields(fields)

    def _fields_from_requirements(self, requirements: list[Any]) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for item in requirements:
            name = self._extract_name(item) or self._infer_field_name(self._text(item))
            if name:
                fields.append({
                    "name": self._camel(name),
                    "type": self._field_type(item),
                    "visibility": "+",
                })
        return self._dedupe_fields(fields)

    def _infer_fields_from_text(self, text: str) -> list[dict[str, Any]]:
        lowered = self._normalize(text)
        fields: list[dict[str, Any]] = []

        for keyword, (field_name, field_type) in self.COMMON_FIELDS.items():
            if keyword in lowered:
                fields.append({"name": field_name, "type": field_type, "visibility": "+"})

        if not fields:
            fields.append({"name": "id", "type": "String", "visibility": "+"})

        return self._dedupe_fields(fields)

    def _field_record(self, field: Any) -> dict[str, Any]:
        if isinstance(field, dict):
            name = field.get("name") or field.get("field") or field.get("data_point") or "field"
            return {
                "name": self._camel(str(name)),
                "type": self._normalize_type(field.get("type", "String")),
                "visibility": "+",
            }
        return {"name": self._camel(str(field)), "type": "String", "visibility": "+"}

    # ------------------------------------------------------------------
    # Traceability and filtering
    # ------------------------------------------------------------------

    def _build_traceability(self, classes: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> list[dict[str, str]]:
        traceability: list[dict[str, str]] = []
        for class_item in classes:
            for req_id in class_item.get("related_requirements", []):
                traceability.append({
                    "source_id": req_id,
                    "source_type": self._guess_source_type(req_id),
                    "mapped_to": class_item.get("name", class_item.get("id")),
                    "mapping_type": "class",
                })
        for relationship in relationships:
            for req_id in relationship.get("related_requirements", []):
                traceability.append({
                    "source_id": req_id,
                    "source_type": self._guess_source_type(req_id),
                    "mapped_to": f"{relationship.get('from')} -> {relationship.get('to')}",
                    "mapping_type": "relationship",
                })
        return traceability

    def _dedupe_classes(self, classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_name: dict[str, dict[str, Any]] = {}
        for class_item in classes:
            name = self._safe_class_name(class_item.get("name", "Class"))
            key = self._normalize(name)
            class_item["name"] = name
            if key not in by_name:
                by_name[key] = class_item
                continue
            by_name[key]["attributes"] = self._dedupe_fields(by_name[key].get("attributes", []) + class_item.get("attributes", []))
            by_name[key]["operations"] = self._dedupe_operations(by_name[key].get("operations", []) + class_item.get("operations", []))
            by_name[key]["related_requirements"] = self._unique(by_name[key].get("related_requirements", []) + class_item.get("related_requirements", []))
        return list(by_name.values())

    def _filter_relationships(self, relationships: list[dict[str, Any]], classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        class_ids = {item.get("id") for item in classes}
        result = []
        seen = set()
        for relationship in relationships:
            if relationship.get("from") not in class_ids or relationship.get("to") not in class_ids:
                continue
            key = (relationship.get("from"), relationship.get("to"), relationship.get("type"), relationship.get("label"))
            if key in seen:
                continue
            seen.add(key)
            result.append(relationship)
        return result

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def _feature_name(self, srs_json: dict[str, Any], sds_json: dict[str, Any]) -> str:
        return srs_json.get("feature_name") or sds_json.get("document_control", {}).get("feature_name") or "Feature"

    def _needs_security_provider(self, srs_json: dict[str, Any]) -> bool:
        return self._has_any(str(srs_json), ["jwt", "token", "otp", "secret", "credential"])

    def _operation_from_requirement(self, text: str) -> str:
        cleaned = self._remove_noise(text)
        match = re.search(r"\b(authenticate|validate|generate|return|create|update|delete|calculate|process|initiate|provide|retrieve|store|save)\b\s+(.+)", cleaned, flags=re.IGNORECASE)
        if match:
            return self._operation_name(f"{match.group(1)} {self._short_topic(match.group(2))}")
        return self._operation_name(cleaned)

    def _operation_name(self, text: str) -> str:
        words = re.findall(r"[a-zA-Z0-9]+", str(text))[:5]
        if not words:
            return "performAction"
        first = words[0].lower()
        rest = "".join(word[:1].upper() + word[1:] for word in words[1:])
        return first + rest

    def _safe_class_name(self, text: str) -> str:
        parts = re.findall(r"[a-zA-Z0-9]+", str(text))
        if not parts:
            return "DesignClass"
        return "".join(part[:1].upper() + part[1:] for part in parts[:5])

    def _camel(self, text: str) -> str:
        class_name = self._safe_class_name(text)
        return class_name[:1].lower() + class_name[1:]

    def _pascal(self, text: str) -> str:
        return self._safe_class_name(text)

    def _short_topic(self, text: str) -> str:
        cleaned = self._remove_noise(text)
        words = re.findall(r"[a-zA-Z0-9]+", cleaned)[:4]
        return " ".join(words) if words else "result"

    def _remove_noise(self, text: str) -> str:
        cleaned = str(text).strip()
        cleaned = re.sub(r"^(the system must|system must|the user must|user must|must|shall|should)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(allow|enable|let|provide|support)\s+", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip(" .")

    def _normalize(self, text: str) -> str:
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _has_any(self, text: str, words: list[str]) -> bool:
        normalized = self._normalize(text)
        return any(word in normalized for word in words)

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    def _extract_name(self, item: Any) -> str:
        if isinstance(item, dict):
            for key in ["name", "field", "data_point", "endpoint", "title"]:
                if item.get(key):
                    return str(item[key]).strip()
            return ""
        return str(item).strip()

    def _text(self, item: Any) -> str:
        if isinstance(item, dict):
            for key in ["description", "payload", "purpose", "expectation", "risk", "mitigation", "name", "field", "endpoint"]:
                if item.get(key):
                    return str(item[key])
            return str(item)
        return str(item)

    def _ids(self, items: Any) -> list[str]:
        ids: list[str] = []
        for item in self._as_list(items):
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
        return self._unique(ids)

    def _related(self, item: Any, fallback: list[str]) -> list[str]:
        if isinstance(item, dict):
            related = item.get("related_requirements")
            if isinstance(related, list) and related:
                return [str(value) for value in related]
            if item.get("id"):
                return [str(item["id"])]
        return fallback

    def _field_type(self, item: Any) -> str:
        if isinstance(item, dict):
            return self._normalize_type(item.get("type", "String"))
        return "String"

    def _normalize_type(self, value: Any) -> str:
        text = str(value or "String")
        lowered = text.lower()
        if "jwt" in lowered or "string" in lowered or "email" in lowered or "password" in lowered:
            return "String"
        if "number" in lowered or "int" in lowered or "decimal" in lowered:
            return "Number"
        if "bool" in lowered:
            return "Boolean"
        if "date" in lowered:
            return "Date"
        return text[:1].upper() + text[1:]

    def _infer_field_name(self, text: str) -> str:
        lowered = self._normalize(text)
        for keyword, (field_name, _field_type) in self.COMMON_FIELDS.items():
            if keyword in lowered:
                return field_name
        return ""

    def _looks_like_bad_inferred_field(self, name: str) -> bool:
        normalized = self._normalize(name)
        bad_fragments = ["requires secure storage", "rieval of hashed", "retrieval of hashed"]
        return any(fragment in normalized for fragment in bad_fragments) or len(name) > 35

    def _dedupe_fields(self, fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for field in fields:
            name = str(field.get("name", "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            result.append(field)
        return result

    def _dedupe_operations(self, operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for operation in operations:
            name = str(operation.get("name", "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            result.append(operation)
        return result

    def _unique(self, items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            value = str(item).strip()
            if value and value not in result:
                result.append(value)
        return result

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
