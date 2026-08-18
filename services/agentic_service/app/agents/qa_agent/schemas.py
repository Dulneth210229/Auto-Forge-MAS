"""
QA Agent internal schemas.

Replaces the earlier aggregate-only shapes (a report that only ever said "3 passed, 1 failed")
with real per-test-case structure: a QaTestCase (what was PLANNED -- name, category, which real
file/function it targets, what inputs/behavior it covers) and a QaTestCaseResult (what actually
happened when it ran -- status, duration, failure message), matched together by name so the
report can show both halves for every test. See agent.py's own module docstring for how
generation and execution produce these.
"""

from pydantic import BaseModel, Field

TEST_CATEGORIES = ("unit", "integration", "regression")


class QAAgentInput(BaseModel):
    feature_id: str


class QaTestCase(BaseModel):
    """One planned test case -- the generation-time half. `test_file` and `method` are filled in
    by the caller (generator.py) after generation, not by the LLM itself."""

    name: str
    category: str = "unit"  # one of TEST_CATEGORIES
    target_file: str = ""
    target_function: str = ""
    inputs: str = ""
    expected_behavior: str = ""
    test_file: str = ""
    method: str = "llm"  # "llm" | "deterministic-fallback"


class QaLLMGenerationResult(BaseModel):
    """The exact JSON shape the LLM is asked to return for one generation call (see prompt.py) --
    parsed via extract_json_object with a graceful fallback on malformed output, the same
    resilience pattern already proven for Security Agent's LLM review layer."""

    test_cases: list[QaTestCase] = Field(default_factory=list)
    test_code: str = ""


class QaTestCaseResult(BaseModel):
    """One test case's real execution outcome, parsed from Jest's --json output. Matched back to
    its QaTestCase by `name` (see agent.py's own matching step) -- Jest's own result has no
    concept of "category"/"inputs"/"expected_behavior", only what actually ran."""

    name: str
    test_file: str = ""
    status: str = "skipped"  # "passed" | "failed" | "skipped"
    duration_ms: int | None = None
    failure_message: str | None = None


class QAAgentOutput(BaseModel):
    qa_report_json: dict = {}
    status: str = "completed"
    framework_used: str = "jest"
    tests_generated: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    artifact_ids: list[str] = []
    message: str = ""
