"""
Unit tests for generator.py -- the "ask nicely -> decide deterministically" LLM generation ladder
(_invoke_llm's malformed/well-formed/unreachable-provider handling) and the deterministic unit
fallback template (_deterministic_unit_fallback), which must still produce real, correct Jest
test code when no LLM is reachable at all. No real LLM/network calls -- llm_provider_service is
mocked at its import site inside generator._invoke_llm.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.qa_agent import generator
from app.agents.qa_agent.schemas import QaLLMGenerationResult


def _mock_provider(raw_output: str):
    provider = MagicMock()
    provider.invoke_agent = AsyncMock(return_value=raw_output)
    return provider


@pytest.mark.asyncio
async def test_invoke_llm_returns_none_on_malformed_json():
    provider = _mock_provider("this is not json at all")
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator._invoke_llm("system", "user")

    assert result is None


@pytest.mark.asyncio
async def test_invoke_llm_returns_none_when_test_code_is_empty():
    raw = '{"test_cases": [{"name": "a test"}], "test_code": ""}'
    provider = _mock_provider(raw)
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator._invoke_llm("system", "user")

    assert result is None


@pytest.mark.asyncio
async def test_invoke_llm_returns_none_when_test_cases_is_empty():
    raw = '{"test_cases": [], "test_code": "test(\\"x\\", () => {});"}'
    provider = _mock_provider(raw)
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator._invoke_llm("system", "user")

    assert result is None


@pytest.mark.asyncio
async def test_invoke_llm_returns_none_when_provider_unreachable():
    provider = MagicMock()
    provider.invoke_agent = AsyncMock(side_effect=ConnectionError("no route to host"))
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator._invoke_llm("system", "user")

    assert result is None


@pytest.mark.asyncio
async def test_invoke_llm_returns_parsed_result_on_well_formed_response():
    raw = (
        '{"test_cases": [{"name": "getItem returns an item", "category": "unit", '
        '"target_file": "lib/api/item.ts", "target_function": "getItem"}], '
        '"test_code": "test(\\"getItem returns an item\\", () => {});"}'
    )
    provider = _mock_provider(raw)
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator._invoke_llm("system", "user")

    assert isinstance(result, QaLLMGenerationResult)
    assert result.test_cases[0].name == "getItem returns an item"
    assert "getItem returns an item" in result.test_code


@pytest.mark.asyncio
async def test_invoke_llm_extracts_json_from_markdown_fenced_response():
    raw = (
        "Here is the test:\n```json\n"
        '{"test_cases": [{"name": "a test"}], "test_code": "test(\\"a test\\", () => {});"}'
        "\n```"
    )
    provider = _mock_provider(raw)
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator._invoke_llm("system", "user")

    assert result is not None
    assert result.test_cases[0].name == "a test"


def test_deterministic_unit_fallback_handles_array_literal_export():
    target = {
        "rel": "lib/seedData.ts",
        "source": "export const SEED_ITEMS = [\n  { id: 1, name: 'a' },\n];\n",
    }

    result = generator._deterministic_unit_fallback(target)

    assert result is not None
    assert len(result.test_cases) == 1
    tc = result.test_cases[0]
    assert tc.target_function == "SEED_ITEMS"
    assert tc.method == "deterministic-fallback"
    assert tc.category == "unit"
    assert "SEED_ITEMS" in result.test_code
    assert 'from "../lib/seedData"' in result.test_code


def test_deterministic_unit_fallback_handles_guarded_async_null_export():
    target = {
        "rel": "lib/mongodb.ts",
        "source": (
            "export async function connectToDatabase() {\n"
            "  if (!process.env.MONGODB_URI) {\n"
            "    return null;\n"
            "  }\n"
            "}\n"
        ),
    }

    result = generator._deterministic_unit_fallback(target)

    assert result is not None
    tc = result.test_cases[0]
    assert tc.target_function == "connectToDatabase"
    assert tc.method == "deterministic-fallback"
    assert "await connectToDatabase()" in result.test_code


def test_deterministic_unit_fallback_returns_none_for_unrecognized_shape():
    target = {
        "rel": "lib/utils.ts",
        "source": "export function add(a: number, b: number): number { return a + b; }\n",
    }

    result = generator._deterministic_unit_fallback(target)

    assert result is None


def test_deterministic_unit_fallback_handles_both_shapes_in_one_file():
    target = {
        "rel": "lib/data.ts",
        "source": (
            "export const ITEMS = [{ id: 1 }];\n\n"
            "export async function getConfig() {\n  if (!process.env.X) {\n    return null;\n  }\n}\n"
        ),
    }

    result = generator._deterministic_unit_fallback(target)

    assert result is not None
    assert len(result.test_cases) == 2
    names = {tc.target_function for tc in result.test_cases}
    assert names == {"ITEMS", "getConfig"}


@pytest.mark.asyncio
async def test_generate_unit_tests_falls_back_to_deterministic_when_llm_unreachable():
    target = {
        "rel": "lib/seedData.ts",
        "exports": ["SEED_ITEMS"],
        "source": "export const SEED_ITEMS = [\n  { id: 1 },\n];\n",
    }
    provider = MagicMock()
    provider.invoke_agent = AsyncMock(side_effect=TimeoutError())
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator.generate_unit_tests(target)

    assert result is not None
    assert result.test_cases[0].method == "deterministic-fallback"


@pytest.mark.asyncio
async def test_generate_unit_tests_returns_none_when_llm_fails_and_no_fallback_shape():
    target = {
        "rel": "lib/utils.ts",
        "exports": ["add"],
        "source": "export function add(a: number, b: number): number { return a + b; }\n",
    }
    provider = MagicMock()
    provider.invoke_agent = AsyncMock(side_effect=TimeoutError())
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator.generate_unit_tests(target)

    assert result is None


@pytest.mark.asyncio
async def test_generate_regression_tests_returns_none_when_no_acceptance_criteria():
    result = await generator.generate_regression_tests([], None)

    assert result is None


@pytest.mark.asyncio
async def test_generate_integration_tests_returns_none_on_llm_failure_no_fallback():
    target = {
        "route_rel": "app/api/items/route.ts",
        "route_source": "export async function GET() { return Response.json([]); }",
        "related_files": [],
    }
    provider = MagicMock()
    provider.invoke_agent = AsyncMock(side_effect=TimeoutError())
    with patch("app.services.llm_provider_service.llm_provider_service.get_provider", return_value=provider):
        result = await generator.generate_integration_tests(target)

    assert result is None
