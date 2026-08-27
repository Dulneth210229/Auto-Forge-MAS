"""
QA Agent test generation.

Three real LLM-backed generation passes (unit/integration/regression), each returning a
QaLLMGenerationResult (structured test_cases metadata + real test_code) parsed via
extract_json_object with a graceful fallback on any failure/malformed response -- mirrors
Security Agent's own "ask nicely -> decide deterministically, never let a bad LLM response fail
the whole run" resilience pattern (security_agent/agent.py's _run_llm_review_layer). Unit
generation additionally has a deterministic template fallback (ported from this module's earlier
implementation) so a run still produces *something* real and correct even with no LLM reachable
at all -- integration/regression generation simply produce nothing for a given target when the
LLM is unavailable, since there is no safe deterministic template for "test this route handler
end to end" or "assert this acceptance criterion holds."
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.qa_agent.prompt import (
    MAX_ROOT_CAUSE_SOURCE_CHARS,
    QA_INTEGRATION_TEST_PROMPT,
    QA_REGRESSION_TEST_PROMPT,
    QA_ROOT_CAUSE_PROMPT,
    QA_UNIT_TEST_PROMPT,
    TEST_CODE_MARKER,
)
from app.agents.qa_agent.schemas import (
    QaLLMGenerationResult,
    QaRootCauseAnalysisResult,
    QaTestCase,
)
from app.core.enums import AgentName
from app.utils.json_utils import extract_json_object
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_generation_response(raw_output: str) -> QaLLMGenerationResult:
    """
    Splits the two-part response format prompt.py's own TEST_CODE_MARKER convention describes
    (JSON test_cases metadata, then the literal marker, then the real test file content) --
    mirrors uiux_agent/component_generator.py's own already-proven HTML_CODE_MARKER `_parse`
    idiom, adapted for the JSON-metadata-plus-marker-plus-code shape QA needs (that precedent has
    no JSON half at all). Splitting on a literal marker string, never fence-hunting, means a fence
    the model puts INSIDE the code, or one wrapping the whole response, can never be confused for
    the split point -- the two failure modes a regex-based fenced-block search would risk.

    Raises ValueError on any malformed shape (missing marker, unparseable JSON, empty code) --
    the caller (_invoke_llm) catches this the same as any other generation failure.
    """
    if TEST_CODE_MARKER not in raw_output:
        raise ValueError(f"Output missing required marker {TEST_CODE_MARKER}.")

    metadata_text, code_section = raw_output.split(TEST_CODE_MARKER, 1)
    parsed = extract_json_object(metadata_text)

    code_section = code_section.strip()
    code_section = re.sub(r"^```(?:typescript|ts|javascript|js)?\s*", "", code_section, flags=re.IGNORECASE)
    code_section = re.sub(r"\s*```$", "", code_section)
    code_section = code_section.strip()
    if not code_section:
        raise ValueError("Test code section must not be empty.")

    parsed["test_code"] = code_section
    return QaLLMGenerationResult.model_validate(parsed)

ARRAY_LITERAL_PATTERN = re.compile(r"export\s+const\s+([A-Za-z0-9_]+)\s*=\s*\[")
GUARDED_ASYNC_NULL_PATTERN = re.compile(
    r"export\s+async\s+function\s+([A-Za-z0-9_]+).*?return\s+null", re.DOTALL
)


async def _invoke_llm(system_prompt: str, user_content: str) -> QaLLMGenerationResult | None:
    """Returns None (never raises) on any failure -- an unreachable provider or an unparseable
    response both degrade to the caller's own fallback handling."""
    try:
        from app.services.llm_provider_service import llm_provider_service

        provider = llm_provider_service.get_provider(agent_name=AgentName.QA.value)
        raw_output = await provider.invoke_agent([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ])
        result = _parse_generation_response(raw_output)
        if not result.test_code.strip() or not result.test_cases:
            return None
        return result
    except Exception as error:  # noqa: BLE001 -- generation must never fail the whole QA run
        logger.warning("QA Agent LLM generation call failed/unparseable, falling back: %s", error)
        return None


def _deterministic_unit_fallback(target: dict[str, Any]) -> QaLLMGenerationResult | None:
    """Ported from this module's earlier implementation: detects the same two narrow,
    mechanically-safe shapes (an exported array literal, an exported async function that
    explicitly guards a null return) and emits a real Jest test file plus matching QaTestCase
    metadata for each. Returns None when neither shape is present -- there is no safe generic
    template for arbitrary exported functions."""
    source = target["source"]
    array_exports = ARRAY_LITERAL_PATTERN.findall(source)
    guarded_exports = GUARDED_ASYNC_NULL_PATTERN.findall(source)
    if not array_exports and not guarded_exports:
        return None

    rel_from_generated_tests = "../" + target["rel"].removesuffix(".ts")
    imported = array_exports + guarded_exports
    import_line = f'import {{ {", ".join(imported)} }} from "{rel_from_generated_tests}";'

    test_cases: list[QaTestCase] = []
    bodies: list[str] = []

    for name in array_exports:
        test_name = f"{name} is a non-empty array with unique ids"
        test_cases.append(QaTestCase(
            name=test_name, category="unit", target_file=target["rel"], target_function=name,
            inputs="the module's own exported array, no external input",
            expected_behavior="the array is non-empty and every entry has a unique id",
            method="deterministic-fallback",
        ))
        bodies.append(f"""test("{test_name}", () => {{
  expect(Array.isArray({name})).toBe(true);
  expect({name}.length).toBeGreaterThan(0);
  const ids = {name}.map((entry) => entry.id);
  expect(new Set(ids).size).toBe(ids.length);
}});""")

    for name in guarded_exports:
        test_name = f"{name}() resolves without throwing when its required env var is unset"
        test_cases.append(QaTestCase(
            name=test_name, category="unit", target_file=target["rel"], target_function=name,
            inputs="called with no real database connection configured",
            expected_behavior="resolves to null or a defined value, never throws",
            method="deterministic-fallback",
        ))
        bodies.append(f"""test("{test_name}", async () => {{
  const result = await {name}();
  expect(result === null || result !== undefined).toBe(true);
}});""")

    test_code = f'{import_line}\n\n{"\n\n".join(bodies)}\n'
    return QaLLMGenerationResult(test_cases=test_cases, test_code=test_code)


async def generate_unit_tests(target: dict[str, Any]) -> QaLLMGenerationResult | None:
    user_content = (
        f"File: {target['rel']}\nExports: {', '.join(target['exports'])}\n\n"
        f"Source:\n```typescript\n{target['source']}\n```"
    )
    result = await _invoke_llm(QA_UNIT_TEST_PROMPT, user_content)
    if result is not None:
        return result
    return _deterministic_unit_fallback(target)


async def generate_integration_tests(target: dict[str, Any]) -> QaLLMGenerationResult | None:
    related_blocks = "\n\n".join(
        f"Related file: {rf['rel']}\n```typescript\n{rf['source']}\n```" for rf in target["related_files"]
    )
    user_content = (
        f"Route Handler: {target['route_rel']}\n"
        f"```typescript\n{target['route_source']}\n```\n\n{related_blocks}"
    )
    return await _invoke_llm(QA_INTEGRATION_TEST_PROMPT, user_content)


async def generate_regression_tests(
    acceptance_criteria: list[dict[str, Any]], route_target: dict[str, Any] | None
) -> QaLLMGenerationResult | None:
    if not acceptance_criteria:
        return None

    criteria_text = "\n".join(
        f"- {criterion.get('id', '')}: {criterion.get('description', criterion)}"
        for criterion in acceptance_criteria
    )
    context = ""
    if route_target is not None:
        context = (
            f"\n\nRoute Handler: {route_target['route_rel']}\n"
            f"```typescript\n{route_target['route_source']}\n```"
        )

    user_content = f"Acceptance criteria:\n{criteria_text}{context}"
    return await _invoke_llm(QA_REGRESSION_TEST_PROMPT, user_content)


async def analyze_failures(
    failures: list[dict[str, Any]], source_by_target_file: dict[str, str]
) -> dict[tuple[str, str], dict[str, str]]:
    """
    ONE batched LLM call (not one per failure -- proportionate to what generation prompts already
    embed today, see prompt.py's own MAX_ROOT_CAUSE_SOURCE_CHARS comment) synthesizing a real
    root_cause + recommendation per failed test. Returns a lookup keyed by (test_file, name) --
    empty dict (never raises) if there are no failures, the provider is unreachable, or the
    response is malformed, so a failed analysis call never blocks the QA report itself from being
    saved (same resilience convention as every other QA/Security LLM call in this codebase).
    """
    if not failures:
        return {}

    try:
        from app.services.llm_provider_service import llm_provider_service

        blocks = []
        for failure in failures:
            source = source_by_target_file.get(failure.get("target_file", ""), "")
            if len(source) > MAX_ROOT_CAUSE_SOURCE_CHARS:
                source = source[:MAX_ROOT_CAUSE_SOURCE_CHARS] + "\n... (truncated)"
            block = (
                f"Test: {failure.get('name', '')}\n"
                f"Test file: {failure.get('test_file', '')}\n"
                f"Target: {failure.get('target_file', '')}::{failure.get('target_function', '')}\n"
                f"Failure message:\n{failure.get('failure_message', '')}"
            )
            if source:
                block += f"\n\nSource of {failure.get('target_file', '')}:\n```typescript\n{source}\n```"
            blocks.append(block)

        provider = llm_provider_service.get_provider(agent_name=AgentName.QA.value)
        raw_output = await provider.invoke_agent([
            {"role": "system", "content": QA_ROOT_CAUSE_PROMPT},
            {"role": "user", "content": "\n\n---\n\n".join(blocks)},
        ])
        parsed = extract_json_object(raw_output)
        result = QaRootCauseAnalysisResult.model_validate(parsed)
        return {
            (entry.test_file, entry.name): {"root_cause": entry.root_cause, "recommendation": entry.recommendation}
            for entry in result.root_causes
        }
    except Exception as error:  # noqa: BLE001 -- root-cause analysis must never fail the whole QA run
        logger.warning("QA Agent root-cause analysis call failed/unparseable, skipping: %s", error)
        return {}
