"""
QA Agent request, response, and report schemas.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Request Schema
# ------------------------------------------------------------------


class TestingRunRequest(BaseModel):
    """
    Request payload for running the QA Agent.
    """

    enable_llm_generation: bool = Field(
        default=True,
        description="Generate tests using the configured LLM.",
    )

    enable_regression: bool = Field(
        default=False,
        description="Generate regression test cases.",
    )

    enable_security_validation: bool = Field(
        default=False,
        description="Generate security validation test cases.",
    )

    human_comment: str | None = Field(
        default=None,
        description="Optional human instructions for the QA Agent.",
        examples=["Generate comprehensive functional test cases."],
    )


# ------------------------------------------------------------------
# Validation Result
# ------------------------------------------------------------------


class ValidationResult(BaseModel):
    """
    Result returned by the Test Validator.
    """

    valid: bool = True

    score: int = Field(
        default=100,
        ge=0,
        le=100,
    )

    validation_errors: list[str] = Field(
        default_factory=list,
    )

    validation_warnings: list[str] = Field(
        default_factory=list,
    )


# ------------------------------------------------------------------
# Generated Test File
# ------------------------------------------------------------------


class GeneratedTestFile(BaseModel):
    """
    Information about a generated test file.
    """

    source_file: str

    test_file: str

    framework: Literal[
        "pytest",
        "jest",
    ] | None = None

    generated_code: str | None = None

    status: Literal[
        "SUCCESS",
        "FAILED",
    ]

    error: str | None = None

    validation_score: int = Field(
        default=100,
        ge=0,
        le=100,
    )

    validation_errors: list[str] = Field(
        default_factory=list,
    )

    validation_warnings: list[str] = Field(
        default_factory=list,
    )


# ------------------------------------------------------------------
# Execution Result
# ------------------------------------------------------------------


class ExecutionResult(BaseModel):
    """
    Aggregated result of executing generated test cases.
    """

    success: bool = False

    exit_code: int = -1

    total_tests: int = 0

    passed: int = 0

    failed: int = 0

    skipped: int = 0

    duration_seconds: float = 0.0

    stdout: str = ""

    stderr: str = ""


# ------------------------------------------------------------------
# Finding Schema
# ------------------------------------------------------------------


class QAFinding(BaseModel):
    """
    Individual QA finding.
    """

    title: str

    description: str

    severity: Literal[
        "Low",
        "Medium",
        "High",
        "Critical",
    ]

    file: str | None = None

    line: int | None = None

    recommendation: str

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )


# ------------------------------------------------------------------
# Summary Schema
# ------------------------------------------------------------------


class QASummary(BaseModel):
    """
    Overall QA summary.
    """

    total_tests: int = 0

    passed: int = 0

    failed: int = 0

    skipped: int = 0

    pass_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )

    status: Literal[
        "GENERATED",
        "PASSED",
        "FAILED",
    ] = "GENERATED"


# ------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------


class QAMetrics(BaseModel):
    """
    QA execution metrics.
    """

    generated_test_files: int = 0

    generation_time_seconds: float = 0.0

    execution_time_seconds: float = 0.0

    total_duration_seconds: float = 0.0


# ------------------------------------------------------------------
# QA Report
# ------------------------------------------------------------------


class QAReport(BaseModel):
    """
    Final QA report.
    """

    feature_id: str

    summary: QASummary

    findings: list[QAFinding] = Field(
        default_factory=list,
    )

    metrics: QAMetrics

    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
    )