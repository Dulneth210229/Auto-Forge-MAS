"""
Unit tests for ArchitectureSequenceModeler (app/agents/architecture_agent/sequence_modeler.py).
No LLM involved -- these exercise the deterministic modeling logic directly.

Covers the two build() paths:
- LLM-specification path (specification's participants/interactions both
  non-empty): the modeler must trust the LLM's participants/interactions
  directly (deterministic id assignment + name resolution only, no fixed
  message template).
- Fallback path (specification empty): the last-resort deterministic
  builder -- unchanged in behavior from before this rewrite, just demoted
  to a private method.
"""

from app.agents.architecture_agent.sequence_modeler import ArchitectureSequenceModeler


class TestLlmSpecificationPath:
    def test_trusts_llm_participants_and_interactions_directly(self):
        modeler = ArchitectureSequenceModeler()

        srs_json = {"feature_name": "Task Search", "user_roles": ["Registered User"]}
        sds_json = {"design_views": {}}
        specification = {
            "diagram_title": "Task Search Sequence Diagram",
            "participants": [
                {"name": "Registered User", "type": "actor"},
                {"name": "TaskSearchBoundary", "type": "boundary"},
                {"name": "TaskSearchController", "type": "control"},
            ],
            "interactions": [
                {
                    "kind": "message", "from": "Registered User", "to": "TaskSearchBoundary",
                    "message": "Type search keyword", "message_type": "sync",
                    "related_requirements": ["FR-001"],
                },
                {
                    "kind": "message", "from": "TaskSearchBoundary", "to": "TaskSearchController",
                    "message": "GET /api/task-search?q=keyword", "message_type": "sync",
                    "related_requirements": ["FR-001"],
                },
                {
                    "kind": "message", "from": "TaskSearchController", "to": "TaskSearchBoundary",
                    "message": "Return matching tasks", "message_type": "return",
                    "related_requirements": ["FR-001"],
                },
            ],
        }

        result = modeler.build(srs_json=srs_json, sds_json=sds_json, sequence_specification_json=specification)

        assert result["diagram_title"] == "Task Search Sequence Diagram"
        assert len(result["participants"]) == 3
        messages = [i for i in result["interactions"] if i["kind"] == "message"]
        assert len(messages) == 3
        assert messages[0]["message"] == "Type search keyword"
        # The old fixed-template strings must never appear when a real
        # specification is trusted.
        all_text = " ".join(m["message"] for m in messages)
        assert "Submit Task Search request" not in all_text

    def test_resolves_participant_names_to_deterministic_ids(self):
        modeler = ArchitectureSequenceModeler()
        specification = {
            "participants": [
                {"name": "User", "type": "actor"},
                {"name": "Boundary", "type": "boundary"},
            ],
            "interactions": [
                {"kind": "message", "from": "User", "to": "Boundary", "message": "Submit", "message_type": "sync"},
            ],
        }

        result = modeler.build(srs_json={"feature_name": "X"}, sds_json={}, sequence_specification_json=specification)

        actor = next(p for p in result["participants"] if p["type"] == "actor")
        boundary = next(p for p in result["participants"] if p["type"] == "boundary")
        message = result["interactions"][0]

        assert message["from"] == actor["id"]
        assert message["to"] == boundary["id"]

    def test_message_referencing_unknown_participant_is_skipped_not_crashed(self):
        modeler = ArchitectureSequenceModeler()
        specification = {
            "participants": [{"name": "User", "type": "actor"}],
            "interactions": [
                {"kind": "message", "from": "User", "to": "GhostParticipant", "message": "Ghost message", "message_type": "sync"},
                {"kind": "message", "from": "User", "to": "User", "message": "Self check", "message_type": "self"},
            ],
        }

        result = modeler.build(srs_json={"feature_name": "X"}, sds_json={}, sequence_specification_json=specification)

        messages = [i for i in result["interactions"] if i["kind"] == "message"]
        assert len(messages) == 1
        assert messages[0]["message"] == "Self check"

    def test_loop_and_async_kinds_are_preserved(self):
        modeler = ArchitectureSequenceModeler()
        specification = {
            "participants": [
                {"name": "User", "type": "actor"},
                {"name": "Service", "type": "control"},
                {"name": "Notifier", "type": "external"},
            ],
            "interactions": [
                {"kind": "loop_start", "condition": "For each item"},
                {"kind": "message", "from": "User", "to": "Service", "message": "Process item", "message_type": "sync"},
                {"kind": "end"},
                {"kind": "message", "from": "Service", "to": "Notifier", "message": "Fire notification", "message_type": "async"},
            ],
        }

        result = modeler.build(srs_json={"feature_name": "X"}, sds_json={}, sequence_specification_json=specification)

        kinds = [i["kind"] for i in result["interactions"]]
        assert kinds == ["loop_start", "message", "end", "message"]
        async_message = result["interactions"][-1]
        assert async_message["message_type"] == "async"

    def test_invalid_message_type_defaults_to_sync(self):
        modeler = ArchitectureSequenceModeler()
        specification = {
            "participants": [{"name": "User", "type": "actor"}, {"name": "Service", "type": "control"}],
            "interactions": [
                {"kind": "message", "from": "User", "to": "Service", "message": "Do thing", "message_type": "not_a_real_type"},
            ],
        }

        result = modeler.build(srs_json={"feature_name": "X"}, sds_json={}, sequence_specification_json=specification)

        assert result["interactions"][0]["message_type"] == "sync"


class TestFallbackPath:
    def test_fallback_produces_a_complete_diagram(self):
        modeler = ArchitectureSequenceModeler()
        srs_json = {
            "feature_name": "Login",
            "user_roles": ["Registered User"],
            "functional_requirements": [{"id": "FR-001", "description": "The system must authenticate a user."}],
        }
        sds_json = {"design_views": {}}

        result = modeler.build(srs_json=srs_json, sds_json=sds_json, sequence_specification_json={})

        assert result["diagram_title"] == "Login Sequence Diagram"
        assert any(p["type"] == "actor" for p in result["participants"])
        assert any(p["type"] == "boundary" for p in result["participants"])
        messages = [i for i in result["interactions"] if i["kind"] == "message"]
        assert len(messages) >= 3

    def test_fallback_is_used_when_participants_present_but_interactions_empty(self):
        """
        A partially-empty specification (e.g. participants without
        interactions) is not "usable" -- falls through to the deterministic
        fallback rather than producing a diagram with no messages.
        """
        modeler = ArchitectureSequenceModeler()
        specification = {"participants": [{"name": "User", "type": "actor"}], "interactions": []}
        srs_json = {"feature_name": "Login", "functional_requirements": [{"id": "FR-001", "description": "x"}]}

        result = modeler.build(srs_json=srs_json, sds_json={"design_views": {}}, sequence_specification_json=specification)

        messages = [i for i in result["interactions"] if i["kind"] == "message"]
        assert len(messages) >= 3
