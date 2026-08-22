"""
Tests for security_agent/deep_scan.py -- the new AI-model deep-code-read scan layer. No real
LLM/HTTP: llm_provider_service.get_provider is mocked to return a fake provider whose
invoke_agent() is fully controlled, isolating the batching/parsing/merge logic itself. Batching
uses a real tmp_path filesystem (no mocks needed for file discovery -- reuses
scanners.list_scannable_files directly).
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.security_agent.deep_scan import (
    MAX_DEEP_SCAN_BATCH_CHARS,
    _batch_files,
    run_ai_model_deep_scan,
)


class TestBatching:
    def test_small_files_grouped_into_one_batch(self, tmp_path):
        (tmp_path / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
        (tmp_path / "b.ts").write_text("export const b = 2;\n", encoding="utf-8")

        batches = _batch_files(tmp_path)

        assert len(batches) == 1
        assert {rel for rel, _ in batches[0]} == {"a.ts", "b.ts"}

    def test_large_file_alone_exceeding_the_cap_becomes_its_own_batch(self, tmp_path):
        (tmp_path / "small.ts").write_text("export const a = 1;\n", encoding="utf-8")
        (tmp_path / "huge.ts").write_text("x" * (MAX_DEEP_SCAN_BATCH_CHARS + 5_000), encoding="utf-8")

        batches = _batch_files(tmp_path)

        assert len(batches) == 2
        rels_by_batch = [{rel for rel, _ in batch} for batch in batches]
        assert {"huge.ts"} in rels_by_batch
        assert {"small.ts"} in rels_by_batch

    def test_no_scannable_files_returns_no_batches(self, tmp_path):
        (tmp_path / "readme.md").write_text("not scannable", encoding="utf-8")
        assert _batch_files(tmp_path) == []

    def test_excluded_directories_are_never_batched(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "dep.ts").write_text("export const x = 1;\n", encoding="utf-8")
        (tmp_path / "real.ts").write_text("export const y = 2;\n", encoding="utf-8")

        batches = _batch_files(tmp_path)

        all_rels = {rel for batch in batches for rel, _ in batch}
        assert all_rels == {"real.ts"}


class TestRunAiModelDeepScan:
    @pytest.mark.asyncio
    async def test_no_scannable_files_returns_empty_findings_without_calling_the_provider(self, tmp_path):
        status, findings = await run_ai_model_deep_scan(tmp_path)

        assert findings == []
        assert "No scannable source files" in status

    @pytest.mark.asyncio
    async def test_well_formed_response_is_parsed_into_security_findings(self, tmp_path):
        (tmp_path / "route.ts").write_text(
            "export async function POST(request) { /* real code */ }\n", encoding="utf-8"
        )
        raw_output = """{
            "findings": [
                {"title": "NoSQL injection", "description": "Client filter merged into query.",
                 "severity": "critical", "file": "route.ts", "line": 3, "cwe": "CWE-943",
                 "root_cause": "req.body fields are spread into the Mongoose filter.",
                 "recommendation": "Only allow a fixed set of known-safe query fields.",
                 "confidence": "high"}
            ]
        }"""
        fake_provider = AsyncMock()
        fake_provider.invoke_agent.return_value = raw_output

        with patch(
            "app.services.llm_provider_service.llm_provider_service.get_provider", return_value=fake_provider
        ):
            status, findings = await run_ai_model_deep_scan(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding["layer"] == "ai_model_deep_scan"
        assert finding["rule_id"] == "SEC-AI-DEEPSCAN"
        assert finding["severity"] == "critical"
        assert finding["file"] == "route.ts"
        assert finding["line"] == 3
        assert finding["cwe"] == "CWE-943"
        assert "NoSQL injection" in finding["message"]
        assert finding["root_cause"] == "req.body fields are spread into the Mongoose filter."
        assert finding["recommendation"] == "Only allow a fixed set of known-safe query fields."
        assert "1 batch" in status

    @pytest.mark.asyncio
    async def test_one_bad_batch_does_not_abort_the_whole_scan(self, tmp_path):
        # Two files, both under the cap individually but each written so they land in SEPARATE
        # batches by forcing a large first file -- simpler: patch _batch_files directly to
        # control batch count deterministically rather than relying on file-size arithmetic.
        with patch(
            "app.agents.security_agent.deep_scan._batch_files",
            return_value=[
                [("bad.ts", "content")],
                [("good.ts", "content")],
            ],
        ):
            fake_provider = AsyncMock()
            fake_provider.invoke_agent.side_effect = [
                "not valid json at all",
                '{"findings": [{"title": "Weak hash rounds", "description": "bcrypt cost 1.", '
                '"severity": "high", "file": "good.ts", "line": 5, "cwe": "CWE-916", '
                '"root_cause": "bcrypt.hash(password, 1)", "recommendation": "Use cost >= 10.", '
                '"confidence": "high"}]}',
            ]

            with patch(
                "app.services.llm_provider_service.llm_provider_service.get_provider",
                return_value=fake_provider,
            ):
                status, findings = await run_ai_model_deep_scan(tmp_path)

        assert len(findings) == 1
        assert findings[0]["file"] == "good.ts"
        assert "1 succeeded, 1 failed" in status

    @pytest.mark.asyncio
    async def test_unreachable_provider_falls_back_to_empty_findings(self, tmp_path):
        (tmp_path / "route.ts").write_text("export const x = 1;\n", encoding="utf-8")

        with patch(
            "app.services.llm_provider_service.llm_provider_service.get_provider",
            side_effect=RuntimeError("provider not configured"),
        ):
            status, findings = await run_ai_model_deep_scan(tmp_path)

        assert findings == []
        assert "unreachable" in status

    @pytest.mark.asyncio
    async def test_findings_get_sequential_distinct_ids_across_batches(self, tmp_path):
        with patch(
            "app.agents.security_agent.deep_scan._batch_files",
            return_value=[[("a.ts", "content")], [("b.ts", "content")]],
        ):
            fake_provider = AsyncMock()
            one_finding = lambda file: (
                '{"findings": [{"title": "t", "description": "d", "severity": "low", '
                f'"file": "{file}", "line": 1, "cwe": null, "root_cause": "r", '
                '"recommendation": "f", "confidence": "low"}]}'
            )
            fake_provider.invoke_agent.side_effect = [one_finding("a.ts"), one_finding("b.ts")]

            with patch(
                "app.services.llm_provider_service.llm_provider_service.get_provider",
                return_value=fake_provider,
            ):
                status, findings = await run_ai_model_deep_scan(tmp_path)

        assert [f["id"] for f in findings] == ["SEC-AI-DEEPSCAN:1", "SEC-AI-DEEPSCAN:2"]
