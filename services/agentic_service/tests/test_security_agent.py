"""
Tests for the Security Agent's severity taxonomy, the LLM review layer's parse/merge/fallback
behavior (a real, confirmed gap this session closed -- the layer used to compute a response and
then discard it entirely), and the graph node's artifact_ids propagation (previously always `[]`
regardless of what the agent actually produced).
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.security_agent import severity
from app.agents.security_agent.agent import SecurityAgent
from app.agents.security_agent.schemas import SecurityAgentOutput


class TestSeverityTaxonomy:
    @pytest.mark.parametrize(
        "raw_severity,expected_tier",
        [
            ("critical", "critical"),
            ("high", "moderate"),
            ("medium", "moderate"),
            ("moderate", "moderate"),  # npm audit's own vocabulary, distinct from "medium"
            ("low", "warning"),
            ("info", "warning"),  # npm audit's own vocabulary
            ("unknown", "warning"),
            ("something-unrecognized", "warning"),  # never raises, degrades to least alarming
            ("CRITICAL", "critical"),  # case-insensitive
        ],
    )
    def test_to_display_tier(self, raw_severity, expected_tier):
        assert severity.to_display_tier(raw_severity) == expected_tier

    def test_count_by_tier(self):
        findings = [
            {"severity": "critical"}, {"severity": "critical"},
            {"severity": "high"}, {"severity": "moderate"},
            {"severity": "low"},
        ]
        counts = severity.count_by_tier(findings)
        assert counts == {"critical": 2, "moderate": 2, "warning": 1}

    def test_count_by_tier_missing_severity_key_defaults_to_unknown_not_a_crash(self):
        counts = severity.count_by_tier([{}])
        assert counts == {"critical": 0, "moderate": 0, "warning": 1}

    @pytest.mark.parametrize(
        "findings,expected_gate",
        [
            ([], "pass"),
            ([{"severity": "low"}], "pass"),
            ([{"severity": "high"}], "review"),
            ([{"severity": "medium"}], "review"),
            ([{"severity": "critical"}], "fail"),
            ([{"severity": "low"}, {"severity": "critical"}], "fail"),
        ],
    )
    def test_gate_decision(self, findings, expected_gate):
        assert severity.gate_decision(findings) == expected_gate


class TestLLMReviewLayer:
    """No real LLM/HTTP -- llm_provider_service.get_provider is mocked to return a fake provider
    whose invoke_agent() is fully controlled, isolating the parse/merge/fallback logic itself."""

    def _make_agent_with_mocked_provider(self, raw_llm_output=None, raises=None):
        agent = SecurityAgent()
        fake_provider = AsyncMock()
        if raises is not None:
            fake_provider.invoke_agent.side_effect = raises
        else:
            fake_provider.invoke_agent.return_value = raw_llm_output
        return agent, fake_provider

    @pytest.mark.asyncio
    async def test_well_formed_response_is_parsed_and_merged(self):
        raw_output = """{
            "additional_findings": [
                {"title": "Missing rate limiting", "description": "No rate limit on login.",
                 "severity": "high", "file": "app/api/login/route.ts", "line": 12,
                 "cwe": "CWE-307", "recommendation": "Add rate limiting.", "confidence": "medium"}
            ],
            "notes": "Reviewed the deterministic findings."
        }"""
        agent, fake_provider = self._make_agent_with_mocked_provider(raw_llm_output=raw_output)

        with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=fake_provider):
            status, findings = await agent._run_llm_review_layer([])

        assert len(findings) == 1
        assert findings[0]["severity"] == "high"
        assert findings[0]["file"] == "app/api/login/route.ts"
        assert findings[0]["line"] == 12
        assert findings[0]["layer"] == "llm"
        assert "Missing rate limiting" in findings[0]["message"]
        assert "1 additional finding" in status
        assert "Reviewed the deterministic findings." in status

    @pytest.mark.asyncio
    async def test_response_wrapped_in_markdown_fences_still_parses(self):
        raw_output = '```json\n{"additional_findings": [], "notes": ""}\n```'
        agent, fake_provider = self._make_agent_with_mocked_provider(raw_llm_output=raw_output)

        with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=fake_provider):
            status, findings = await agent._run_llm_review_layer([])

        assert findings == []
        assert "ran successfully" in status

    @pytest.mark.asyncio
    async def test_malformed_json_falls_back_to_empty_findings_not_a_crash(self):
        agent, fake_provider = self._make_agent_with_mocked_provider(raw_llm_output="not json at all")

        with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=fake_provider):
            status, findings = await agent._run_llm_review_layer([])

        assert findings == []
        assert "could not be parsed" in status

    @pytest.mark.asyncio
    async def test_response_missing_required_shape_falls_back_gracefully(self):
        # Valid JSON, but not the expected shape at all (e.g. a plain list instead of an object).
        agent, fake_provider = self._make_agent_with_mocked_provider(raw_llm_output="[1, 2, 3]")

        with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=fake_provider):
            status, findings = await agent._run_llm_review_layer([])

        assert findings == []
        assert "could not be parsed" in status

    @pytest.mark.asyncio
    async def test_unreachable_provider_falls_back_gracefully(self):
        agent, fake_provider = self._make_agent_with_mocked_provider(raises=ConnectionError("no route to host"))

        with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=fake_provider):
            status, findings = await agent._run_llm_review_layer([])

        assert findings == []
        assert "unreachable" in status

    @pytest.mark.asyncio
    async def test_get_provider_itself_raising_falls_back_gracefully(self):
        agent = SecurityAgent()

        with patch(
            "app.services.llm_provider_service.llm_provider_service.get_provider",
            side_effect=RuntimeError("provider not configured"),
        ):
            status, findings = await agent._run_llm_review_layer([])

        assert findings == []
        assert "unreachable" in status


class TestSecurityNodeArtifactIds:
    def test_security_node_returns_real_artifact_ids_not_empty(self):
        from app.services.graph_orchestrator_service import _security_node

        fake_output = SecurityAgentOutput(
            status="completed",
            gate_decision="fail",
            findings_count=2,
            critical_count=1,
            moderate_count=1,
            warning_count=0,
            artifact_ids=["artifact_json_1", "artifact_md_1"],
            message="2 finding(s), gate=fail.",
        )

        with patch(
            "app.services.graph_orchestrator_service.security_agent.run",
            new=AsyncMock(return_value=fake_output),
        ):
            result = _security_node({"feature_id": "fake_feature", "human_comment": "prior"})

        assert result == {
            "last_agent": "security",
            "last_artifact_ids": ["artifact_json_1", "artifact_md_1"],
            "human_comment": None,
        }
