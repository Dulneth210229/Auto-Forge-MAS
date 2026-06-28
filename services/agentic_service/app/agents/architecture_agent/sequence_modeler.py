"""
Architecture Agent Sequence Diagram Modeler.

Purpose:
Build a standard UML Sequence Diagram model from approved SRS and SDS data.

Design principle:
- This file is feature-independent.
- It does not hardcode Login, Cart, Payment, LMS, or any other feature.
- It derives lifelines and messages from approved SRS/SDS sections.
- The LLM does not directly generate PlantUML.

UML sequence rules applied:
- External user roles are actors.
- UI/API boundary is represented as a boundary lifeline.
- Controller/service/repository are internal control lifelines when applicable.
- Data entities or data stores are entity/database lifelines when applicable.
- Messages are ordered from top to bottom.
- Main success flow is represented first.
- Alternative and exception behaviour is represented using alt/else fragments.
- NFRs, constraints, risks, and architecture notes are not modelled as messages.
"""

from __future__ import annotations

import re
from typing import Any


class ArchitectureSequenceModeler:
    """
    Builds sequence_diagram_json from SRS and SDS.
    """

    def build(self, srs_json: dict[str, Any], sds_json: dict[str, Any]) -> dict[str, Any]:
        feature_name = self._feature_name(srs_json, sds_json)
        design_views = sds_json.get("design_views", {}) if isinstance(sds_json, dict) else {}
        interface_view = design_views.get("interface_view", {}) if isinstance(design_views, dict) else {}
        data_view = design_views.get("data_view", {}) if isinstance(design_views, dict) else {}
        behavior_view = design_views.get("behavior_view", {}) if isinstance(design_views, dict) else {}

        actors = self._actors(srs_json, sds_json)
        endpoints = self._as_list(interface_view.get("api_endpoints"))
        request_models = self._as_list(interface_view.get("request_models"))
        response_models = self._as_list(interface_view.get("response_models"))
        data_entities = self._as_list(data_view.get("data_entities"))
        validation_rules = self._as_list(srs_json.get("validation_rules"))
        functional_requirements = self._as_list(srs_json.get("functional_requirements"))
        acceptance_criteria = self._as_list(srs_json.get("acceptance_criteria"))
        output_requirements = self._as_list(srs_json.get("output_requirements"))

        participants = self._build_participants(
            feature_name=feature_name,
            actors=actors,
            data_entities=data_entities,
            srs_json=srs_json,
        )

        actor_id = participants[0]["id"]
        boundary_id = self._participant_id(participants, "boundary")
        controller_id = self._participant_id(participants, "control", suffix="Controller")
        service_id = self._participant_id(participants, "control", suffix="Service")
        repository_id = self._participant_id(participants, "entity", suffix="Repository")
        datastore_id = self._participant_id(participants, "database")
        external_provider_id = self._participant_id(participants, "external")

        main_endpoint = self._main_endpoint(endpoints, feature_name)
        request_model_name = self._first_name(request_models, f"{self._pascal(feature_name)}Request")
        success_response_name = self._success_response_name(response_models, feature_name)
        error_response_name = self._error_response_name(response_models, feature_name)
        main_fr_ids = self._ids(functional_requirements)
        validation_ids = self._ids(validation_rules)

        interactions: list[dict[str, Any]] = []

        interactions.append(self._message(
            actor_id,
            boundary_id,
            f"Submit {feature_name} request",
            "sync",
            self._related_ids_for_user_start(srs_json),
        ))

        interactions.append(self._message(
            boundary_id,
            controller_id,
            self._endpoint_message(main_endpoint, request_model_name),
            "sync",
            self._related(main_endpoint, main_fr_ids),
        ))

        if validation_rules:
            interactions.append(self._message(
                controller_id,
                controller_id,
                "Validate request input",
                "self",
                validation_ids,
            ))

        interactions.append(self._fragment("alt_start", "Valid request and successful processing"))

        interactions.append(self._message(
            controller_id,
            service_id,
            f"Process {feature_name} business rules",
            "sync",
            main_fr_ids,
        ))

        if repository_id and datastore_id:
            interactions.append(self._message(
                service_id,
                repository_id,
                "Retrieve required data",
                "sync",
                self._related_ids_for_data(srs_json),
            ))
            interactions.append(self._message(
                repository_id,
                datastore_id,
                "Read matching record",
                "sync",
                self._related_ids_for_data(srs_json),
            ))
            interactions.append(self._message(
                datastore_id,
                repository_id,
                "Return stored data",
                "return",
                self._related_ids_for_data(srs_json),
            ))
            interactions.append(self._message(
                repository_id,
                service_id,
                "Return data result",
                "return",
                self._related_ids_for_data(srs_json),
            ))

        interactions.append(self._message(
            service_id,
            service_id,
            "Apply feature validation rules",
            "self",
            self._ids(functional_requirements),
        ))

        if external_provider_id:
            interactions.append(self._message(
                service_id,
                external_provider_id,
                "Generate required output credential/token",
                "sync",
                self._related_ids_for_token_or_output(srs_json, output_requirements),
            ))
            interactions.append(self._message(
                external_provider_id,
                service_id,
                "Return generated value",
                "return",
                self._related_ids_for_token_or_output(srs_json, output_requirements),
            ))

        interactions.append(self._message(
            service_id,
            controller_id,
            f"Return {success_response_name}",
            "return",
            self._related_ids_for_success(acceptance_criteria, functional_requirements),
        ))
        interactions.append(self._message(
            controller_id,
            boundary_id,
            f"Send {success_response_name}",
            "return",
            self._related_ids_for_success(acceptance_criteria, functional_requirements),
        ))
        interactions.append(self._message(
            boundary_id,
            actor_id,
            "Show success result",
            "return",
            self._related_ids_for_success(acceptance_criteria, functional_requirements),
        ))

        exception_criteria = self._exception_criteria(acceptance_criteria)
        if exception_criteria:
            interactions.append(self._fragment("else", "Invalid request or failed processing"))
            interactions.append(self._message(
                controller_id,
                boundary_id,
                f"Send {error_response_name}",
                "return",
                self._ids(exception_criteria),
            ))
            interactions.append(self._message(
                boundary_id,
                actor_id,
                "Display clear error message",
                "return",
                self._ids(exception_criteria) + self._ids(self._nfr_error_messages(srs_json)),
            ))

        interactions.append(self._fragment("end", ""))

        alternative_criteria = self._alternative_criteria(acceptance_criteria)
        alternative_endpoint = self._alternative_endpoint(endpoints, main_endpoint)
        if alternative_criteria or alternative_endpoint:
            interactions.append(self._fragment("opt_start", "Optional or alternative user flow"))
            interactions.append(self._message(
                actor_id,
                boundary_id,
                "Select alternative feature action",
                "sync",
                self._ids(alternative_criteria),
            ))
            interactions.append(self._message(
                boundary_id,
                controller_id,
                self._endpoint_message(alternative_endpoint, request_model_name) if alternative_endpoint else "Request alternative flow",
                "sync",
                self._related(alternative_endpoint, self._ids(alternative_criteria)),
            ))
            interactions.append(self._message(
                controller_id,
                boundary_id,
                "Return alternative flow response",
                "return",
                self._ids(alternative_criteria),
            ))
            interactions.append(self._fragment("end", ""))

        return {
            "diagram_title": f"{feature_name} Sequence Diagram",
            "feature_name": feature_name,
            "participants": participants,
            "interactions": interactions,
            "traceability": self._build_traceability(interactions),
            "rules_applied": [
                "Participants are lifelines derived from SRS roles and SDS design views.",
                "Main success flow is represented before alternatives and exceptions.",
                "Alternative and exception scenarios use UML combined fragments.",
                "NFRs, constraints, risks, and architecture notes are not represented as messages.",
                "Messages reference SRS IDs where possible.",
            ],
        }

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    def _build_participants(
        self,
        feature_name: str,
        actors: list[str],
        data_entities: list[Any],
        srs_json: dict[str, Any],
    ) -> list[dict[str, Any]]:
        participants: list[dict[str, Any]] = []

        for index, actor in enumerate(actors or ["User"], start=1):
            participants.append({
                "id": f"ACTOR_{index:03d}",
                "name": actor,
                "type": "actor",
                "description": "External user role that initiates the feature interaction.",
            })

        feature_pascal = self._pascal(feature_name)
        participants.extend([
            {
                "id": "BOUNDARY_001",
                "name": f"{feature_pascal}Boundary",
                "type": "boundary",
                "description": "UI or API boundary that receives the external request.",
            },
            {
                "id": "CONTROL_001",
                "name": f"{feature_pascal}Controller",
                "type": "control",
                "description": "Controller that coordinates request validation and response handling.",
            },
            {
                "id": "CONTROL_002",
                "name": f"{feature_pascal}Service",
                "type": "control",
                "description": "Service that applies feature business rules.",
            },
        ])

        if data_entities or srs_json.get("data_requirements"):
            participants.append({
                "id": "ENTITY_001",
                "name": f"{feature_pascal}Repository",
                "type": "entity",
                "description": "Data access lifeline for feature persistence/retrieval.",
            })
            participants.append({
                "id": "DATABASE_001",
                "name": self._data_store_name(data_entities, feature_name),
                "type": "database",
                "description": "Persistent data store or data entity used by the feature.",
            })

        if self._needs_external_provider(srs_json):
            participants.append({
                "id": "EXTERNAL_001",
                "name": "SecurityTokenProvider",
                "type": "external",
                "description": "External/internal provider responsible for generated security output when required by SRS.",
            })

        return participants

    def _actors(self, srs_json: dict[str, Any], sds_json: dict[str, Any]) -> list[str]:
        candidates: list[Any] = []
        candidates.extend(self._as_list(srs_json.get("user_roles")))
        context_view = sds_json.get("design_views", {}).get("context_view", {}) if isinstance(sds_json, dict) else {}
        if isinstance(context_view, dict):
            candidates.extend(self._as_list(context_view.get("actors")))

        names: list[str] = []
        for candidate in candidates:
            name = self._extract_name(candidate)
            if name and name.lower() not in [item.lower() for item in names]:
                names.append(self._title(name))

        return names or ["User"]

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------

    def _message(self, source: str, target: str, message: str, message_type: str, related: list[str]) -> dict[str, Any]:
        return {
            "kind": "message",
            "from": source,
            "to": target,
            "message": self._short(message, 80),
            "message_type": message_type,
            "related_requirements": self._unique(related),
        }

    def _fragment(self, kind: str, condition: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "condition": condition,
        }

    def _build_traceability(self, interactions: list[dict[str, Any]]) -> list[dict[str, str]]:
        traceability: list[dict[str, str]] = []
        for item in interactions:
            if item.get("kind") != "message":
                continue
            for req_id in item.get("related_requirements", []):
                traceability.append({
                    "source_id": req_id,
                    "source_type": self._guess_source_type(req_id),
                    "mapped_to": item.get("message", "message"),
                    "mapping_type": "sequence_message",
                })
        return traceability

    # ------------------------------------------------------------------
    # Requirement classification
    # ------------------------------------------------------------------

    def _exception_criteria(self, acceptance_criteria: list[Any]) -> list[Any]:
        return [item for item in acceptance_criteria if self._has_any(self._text(item), ["invalid", "error", "fail", "prevent", "denied", "unauthorized", "incorrect"])]

    def _alternative_criteria(self, acceptance_criteria: list[Any]) -> list[Any]:
        return [item for item in acceptance_criteria if self._has_any(self._text(item), ["click", "optional", "alternative", "recover", "forgot", "reset", "redirect", "directed", "link", "initiate"])]

    def _nfr_error_messages(self, srs_json: dict[str, Any]) -> list[Any]:
        return [item for item in self._as_list(srs_json.get("non_functional_requirements")) if self._has_any(self._text(item), ["error", "message", "clear", "non technical"])]

    def _related_ids_for_user_start(self, srs_json: dict[str, Any]) -> list[str]:
        return self._ids(srs_json.get("functional_requirements", []))[:1]

    def _related_ids_for_data(self, srs_json: dict[str, Any]) -> list[str]:
        ids: list[str] = []
        ids.extend(self._ids(srs_json.get("data_requirements", [])))
        ids.extend(self._ids([item for item in self._as_list(srs_json.get("functional_requirements")) if self._has_any(self._text(item), ["validate", "database", "stored", "record", "retrieve"])]))
        return ids

    def _related_ids_for_token_or_output(self, srs_json: dict[str, Any], output_requirements: list[Any]) -> list[str]:
        ids: list[str] = []
        ids.extend(self._ids([item for item in self._as_list(srs_json.get("functional_requirements")) if self._has_any(self._text(item), ["token", "jwt", "generate", "return"])]))
        ids.extend(self._ids(output_requirements))
        return ids

    def _related_ids_for_success(self, acceptance_criteria: list[Any], functional_requirements: list[Any]) -> list[str]:
        ids = self._ids([item for item in acceptance_criteria if not self._has_any(self._text(item), ["invalid", "error", "fail", "forgot", "reset", "recover", "click"])])
        if ids:
            return ids
        return self._ids(functional_requirements)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def _feature_name(self, srs_json: dict[str, Any], sds_json: dict[str, Any]) -> str:
        return (
            srs_json.get("feature_name")
            or sds_json.get("document_control", {}).get("feature_name")
            or "Feature"
        )

    def _participant_id(self, participants: list[dict[str, Any]], participant_type: str, suffix: str | None = None) -> str:
        for participant in participants:
            if participant.get("type") != participant_type:
                continue
            if suffix and not str(participant.get("name", "")).endswith(suffix):
                continue
            return participant["id"]
        return ""

    def _main_endpoint(self, endpoints: list[Any], feature_name: str) -> dict[str, Any] | None:
        if not endpoints:
            return None
        feature_token = self._normalize(feature_name)
        for endpoint in endpoints:
            text = self._normalize(self._text(endpoint))
            if feature_token and feature_token in text:
                return endpoint if isinstance(endpoint, dict) else {"purpose": str(endpoint)}
        return endpoints[0] if isinstance(endpoints[0], dict) else {"purpose": str(endpoints[0])}

    def _alternative_endpoint(self, endpoints: list[Any], main_endpoint: dict[str, Any] | None) -> dict[str, Any] | None:
        for endpoint in endpoints:
            if endpoint is main_endpoint:
                continue
            text = self._normalize(self._text(endpoint))
            if self._has_any(text, ["forgot", "recover", "reset", "alternative", "initiate"]):
                return endpoint if isinstance(endpoint, dict) else {"purpose": str(endpoint)}
        if len(endpoints) > 1:
            endpoint = endpoints[1]
            return endpoint if isinstance(endpoint, dict) else {"purpose": str(endpoint)}
        return None

    def _endpoint_message(self, endpoint: dict[str, Any] | None, request_model_name: str) -> str:
        if not endpoint:
            return f"Call feature endpoint with {request_model_name}"
        method = endpoint.get("method", "CALL")
        path = endpoint.get("endpoint", "feature endpoint")
        return f"{method} {path}({request_model_name})"

    def _related(self, item: Any, fallback: list[str]) -> list[str]:
        if isinstance(item, dict):
            related = item.get("related_requirements") or []
            if isinstance(related, list) and related:
                return [str(value) for value in related]
        return fallback

    def _success_response_name(self, response_models: list[Any], feature_name: str) -> str:
        for model in response_models:
            if isinstance(model, dict) and str(model.get("type", "")).lower() == "success":
                return str(model.get("name") or f"{self._pascal(feature_name)}SuccessResponse")
        return f"{self._pascal(feature_name)}SuccessResponse"

    def _error_response_name(self, response_models: list[Any], feature_name: str) -> str:
        for model in response_models:
            if isinstance(model, dict) and str(model.get("type", "")).lower() == "error":
                return str(model.get("name") or f"{self._pascal(feature_name)}ErrorResponse")
        return f"{self._pascal(feature_name)}ErrorResponse"

    def _first_name(self, items: list[Any], fallback: str) -> str:
        for item in items:
            if isinstance(item, dict) and item.get("name"):
                return str(item["name"])
        return fallback

    def _data_store_name(self, data_entities: list[Any], feature_name: str) -> str:
        for entity in data_entities:
            name = self._extract_name(entity)
            if name:
                return self._pascal(name)
        return f"{self._pascal(feature_name)}DataStore"

    def _needs_external_provider(self, srs_json: dict[str, Any]) -> bool:
        text = self._normalize(str(srs_json))
        return self._has_any(text, ["jwt", "token", "otp", "email", "notification"])

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    def _extract_name(self, item: Any) -> str:
        if isinstance(item, dict):
            for key in ["name", "role", "actor", "data_point", "field", "endpoint", "title"]:
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
        result: list[str] = []
        for item in self._as_list(items):
            if isinstance(item, dict) and item.get("id"):
                result.append(str(item["id"]))
        return self._unique(result)

    def _normalize(self, text: str) -> str:
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _has_any(self, text: str, words: list[str]) -> bool:
        normalized = self._normalize(text)
        return any(word in normalized for word in words)

    def _pascal(self, text: str) -> str:
        parts = re.findall(r"[a-zA-Z0-9]+", str(text))
        return "".join(part[:1].upper() + part[1:] for part in parts) or "Feature"

    def _title(self, text: str) -> str:
        return " ".join(word[:1].upper() + word[1:] for word in str(text).split())

    def _short(self, text: str, limit: int) -> str:
        text = re.sub(r"\s+", " ", str(text)).strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

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
