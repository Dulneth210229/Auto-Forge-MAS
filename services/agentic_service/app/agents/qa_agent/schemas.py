"""
QA Agent internal schemas.

Replaces the earlier aggregate-only shapes (a report that only ever said "3 passed, 1 failed")
with real per-test-case structure: a QaTestCase (what was PLANNED -- name, category, which real
file/function it targets, what inputs/behavior it covers) and a QaTestCaseResult (what actually
happened when it ran -- status, duration, failure message), matched together by name so the
report can show both halves for every test. See agent.py's own module docstring for how
generation and execution produce these.
"""

from datetime import datetime

from pydantic import BaseModel, Field

TEST_CATEGORIES = ("unit", "integration", "regression")


class QAAgentInput(BaseModel):
    feature_id: str


class QASummary(BaseModel):
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    status: str = "GENERATED"


class QAMetrics(BaseModel):
    generated_test_files: int = 0
    generation_time_seconds: float = 0.0
    execution_time_seconds: float = 0.0
    total_duration_seconds: float = 0.0


class QAFinding(BaseModel):
    title: str
    description: str
    severity: str
    recommendation: str
    confidence: float = 0.0
    file: str | None = None
    line: int | None = None


class GeneratedTestFile(BaseModel):
    source_file: str = ""
    status: str = "GENERATED"
    error: str | None = None


class ExecutionResult(BaseModel):
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0


class QAReport(BaseModel):
    feature_id: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)
    summary: QASummary = Field(default_factory=QASummary)
    findings: list[QAFinding] = Field(default_factory=list)
    metrics: QAMetrics = Field(default_factory=QAMetrics)


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
    # LLM-synthesized explanation of a failure (see agent.py's _analyze_failures) -- distinct from
    # failure_message (Jest's own raw assertion/stack-trace text): root_cause explains WHY it
    # actually failed, recommendation says what to change. Both stay None (never block the report)
    # if the analysis call is unreachable/fails, or for a passed/skipped test.
    root_cause: str | None = None
    recommendation: str | None = None


class QaRootCauseEntry(BaseModel):
    """One entry in the batched root-cause analysis call's response (see agent.py's
    _analyze_failures / prompt.py's QA_ROOT_CAUSE_PROMPT) -- matched back to its QaTestCaseResult
    by (test_file, name), the same pairing convention already used to match execution results to
    planned test cases."""

    test_file: str = ""
    name: str = ""
    root_cause: str = ""
    recommendation: str = ""


class QaRootCauseAnalysisResult(BaseModel):
    root_causes: list[QaRootCauseEntry] = Field(default_factory=list)

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
