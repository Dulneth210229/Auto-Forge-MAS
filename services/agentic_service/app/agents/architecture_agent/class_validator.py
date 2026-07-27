"""
Architecture Agent Class Diagram Validator.

Purpose:
Validate generated UML Class Diagram JSON before PlantUML rendering.

Feature-independent rules:
- Classes must be structural design elements.
- Relationships must connect existing classes.
- DTO/entity/control/service/repository classes are allowed.
- NFRs, risks, constraints, and use-case-only phrases must not become classes.
- Functional/data/interface requirements should be traceable where possible.
"""

from __future__ import annotations

import re
from typing import Any


class ClassDiagramValidationError(Exception):
    """Raised when the generated class diagram model is invalid."""


class ClassDiagramValidator:
    """
    Pass/fail validator for class_diagram_json.
    """

    INVALID_CLASS_TERMS = [
        "performance", "response time", "responsive ui", "mern stack", "mvc",
        "architecture style", "risk", "constraint", "nfr", "use case diagram",
    ]

    ALLOWED_RELATIONSHIP_TYPES = {
        "association", "dependency", "aggregation", "composition", "inheritance", "generalization"
    }

    # Standard UML multiplicity notation: 0, 1, *, a plain integer, or a
    # range of any two of those (e.g. "0..1", "0..*", "1..*", "2..5").
    MULTIPLICITY_PATTERN = re.compile(r"^(0|1|\*|\d+)(\.\.(0|1|\*|\d+))?$")

    # Only these relationship kinds carry real cardinality between two
    # classes in standard UML -- dependency/inheritance/generalization do not.
    MULTIPLICITY_REQUIRED_TYPES = {"association", "aggregation", "composition"}

    # A dto/entity class with ONLY these attribute names is indistinguishable
    # from the deterministic fallback's placeholder "id: String" default --
    # not a real, feature-specific structural element.
    GENERIC_ATTRIBUTE_NAMES = {"id", "value", "field", "data"}

    def validate(self, srs_json: dict[str, Any], class_json: dict[str, Any]) -> None:
        errors: list[str] = []
        errors.extend(self._validate_structure(class_json))
        errors.extend(self._validate_classes(class_json))
        errors.extend(self._validate_class_quality(class_json))
        errors.extend(self._validate_relationships(class_json))
        errors.extend(self._validate_multiplicity(class_json))
        errors.extend(self._validate_traceability(srs_json, class_json))

        if errors:
            raise ClassDiagramValidationError("; ".join(errors))

    def _validate_structure(self, class_json: dict[str, Any]) -> list[str]:
        if not isinstance(class_json, dict):
            return ["class_diagram_json must be a JSON object."]

        errors: list[str] = []
        for key in ["diagram_title", "classes", "relationships"]:
            if key not in class_json:
                errors.append(f"class_diagram_json missing required key: {key}")

        if not isinstance(class_json.get("classes", []), list) or not class_json.get("classes", []):
            errors.append("Class diagram must have at least one class.")

        if not isinstance(class_json.get("relationships", []), list):
            errors.append("class_diagram_json.relationships must be a list.")

        return errors

    def _validate_classes(self, class_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        seen_names: set[str] = set()

        for class_item in class_json.get("classes", []):
            if not isinstance(class_item, dict):
                errors.append("Each class diagram class must be a JSON object.")
                continue

            class_id = str(class_item.get("id", "")).strip()
            name = str(class_item.get("name", "")).strip()

            if not class_id or not name:
                errors.append("Each class must have id and name.")
                continue

            normalized_name = self._normalize(name)
            if normalized_name in seen_names:
                errors.append(f"Duplicate class name found: {name}")
            seen_names.add(normalized_name)

            if self._contains_any(normalized_name, self.INVALID_CLASS_TERMS):
                errors.append(f"Non-structural item used as class: {name}")

            attributes = class_item.get("attributes", [])
            operations = class_item.get("operations", [])
            if not isinstance(attributes, list):
                errors.append(f"Class attributes must be a list: {name}")
            if not isinstance(operations, list):
                errors.append(f"Class operations must be a list: {name}")

        return errors

    def _validate_relationships(self, class_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        class_ids = {
            str(item.get("id"))
            for item in class_json.get("classes", [])
            if isinstance(item, dict) and item.get("id")
        }

        for relationship in class_json.get("relationships", []):
            if not isinstance(relationship, dict):
                errors.append("Each class relationship must be a JSON object.")
                continue

            source = str(relationship.get("from", "")).strip()
            target = str(relationship.get("to", "")).strip()
            relation_type = str(relationship.get("type", "")).strip()

            if source not in class_ids:
                errors.append(f"Class relationship source is not a class: {source}")
            if target not in class_ids:
                errors.append(f"Class relationship target is not a class: {target}")
            if relation_type not in self.ALLOWED_RELATIONSHIP_TYPES:
                errors.append(f"Invalid class relationship type: {relation_type}")

        return errors

    def _validate_class_quality(self, class_json: dict[str, Any]) -> list[str]:
        """
        Flags anemic dto/entity classes (zero attributes) and dto/entity
        classes whose attributes are ALL generic placeholders -- the
        confirmed real failure mode of the old deterministic fallback,
        which defaulted to a single "id: String" field whenever it couldn't
        infer real fields from free text. A class with a genuine mix of
        real and generic-named fields is not flagged.
        """
        errors: list[str] = []

        for class_item in class_json.get("classes", []):
            if not isinstance(class_item, dict):
                continue

            stereotype = str(class_item.get("stereotype", "")).strip().lower()
            if stereotype not in ("dto", "entity"):
                continue

            name = str(class_item.get("name", "")).strip()
            attributes = class_item.get("attributes", [])
            if not isinstance(attributes, list):
                continue

            if not attributes:
                errors.append(
                    f"{stereotype.title()} class '{name}' has no attributes -- an anemic "
                    f"DTO/entity is not a useful class diagram element."
                )
                continue

            attribute_names = {
                self._normalize(str(attribute.get("name", "")))
                for attribute in attributes
                if isinstance(attribute, dict)
            }
            attribute_names.discard("")

            if attribute_names and attribute_names.issubset(self.GENERIC_ATTRIBUTE_NAMES):
                errors.append(
                    f"{stereotype.title()} class '{name}' only has placeholder attributes "
                    f"({sorted(attribute_names)}) -- add real, feature-specific fields."
                )

        return errors

    def _validate_multiplicity(self, class_json: dict[str, Any]) -> list[str]:
        """
        Every association/aggregation/composition relationship must carry
        standard UML multiplicity notation on both ends -- the confirmed
        real gap in the old builder/schema (no cardinality notation existed
        at all). dependency/inheritance/generalization do not carry
        cardinality in standard UML and are exempt.
        """
        errors: list[str] = []

        for relationship in class_json.get("relationships", []):
            if not isinstance(relationship, dict):
                continue

            relation_type = str(relationship.get("type", "")).strip().lower()
            if relation_type not in self.MULTIPLICITY_REQUIRED_TYPES:
                continue

            source_multiplicity = str(relationship.get("source_multiplicity", "")).strip()
            target_multiplicity = str(relationship.get("target_multiplicity", "")).strip()
            label = f"{relationship.get('from')} -> {relationship.get('to')}"

            if not source_multiplicity or not target_multiplicity:
                errors.append(
                    f"{relation_type.title()} relationship {label} is missing UML multiplicity "
                    f"(source_multiplicity/target_multiplicity)."
                )
                continue

            if not self.MULTIPLICITY_PATTERN.match(source_multiplicity) or not self.MULTIPLICITY_PATTERN.match(target_multiplicity):
                errors.append(
                    f"{relation_type.title()} relationship {label} has non-standard multiplicity "
                    f"notation: '{source_multiplicity}'/'{target_multiplicity}' (expected forms "
                    f"like 1, 0..1, 0..*, 1..*)."
                )

        return errors

    def _validate_traceability(self, srs_json: dict[str, Any], class_json: dict[str, Any]) -> list[str]:
        required_ids: list[str] = []
        required_ids.extend(self._collect_ids(srs_json.get("functional_requirements", [])))
        required_ids.extend(self._collect_ids(srs_json.get("data_requirements", [])))
        required_ids.extend(self._collect_ids(srs_json.get("api_expectations", [])))

        if not required_ids:
            return []

        covered: set[str] = set()
        for class_item in class_json.get("classes", []):
            if isinstance(class_item, dict):
                covered.update(map(str, class_item.get("related_requirements", []) or []))
        for trace in class_json.get("traceability", []):
            if isinstance(trace, dict) and trace.get("source_id"):
                covered.add(str(trace["source_id"]))

        missing_fr_ids = [req_id for req_id in self._collect_ids(srs_json.get("functional_requirements", [])) if req_id not in covered]
        if missing_fr_ids:
            return [f"Class diagram missing traceability for FR IDs: {missing_fr_ids}"]

        return []

    def _collect_ids(self, items: Any) -> list[str]:
        ids: list[str] = []
        if not isinstance(items, list):
            return ids
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
        return ids

    def _normalize(self, text: str) -> str:
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)
