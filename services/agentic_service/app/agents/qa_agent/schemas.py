"""
QA Agent request, response, and report schemas.
"""

from datetime import datetime
from typing import List, Optional

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
        description="Generate tests using the configured LLM."
    )

    enable_regression: bool = Field(
        default=False,
        description="Generate regression test cases."
    )

    enable_security_validation: bool = Field(
        default=False,
        description="Generate security validation test cases."
    )

    human_comment: str | None = Field(
        default=None,
        example="Generate comprehensive functional test cases."
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

    generated_code: str | None = None

    status: str

    error: Optional[str] = None


# ------------------------------------------------------------------
# Finding Schema
# ------------------------------------------------------------------

class QAFinding(BaseModel):
    """
    Individual QA finding.
    """

    title: str

    description: str

    severity: str = Field(
        description="Low | Medium | High | Critical"
    )

    file: Optional[str] = None

    line: Optional[int] = None

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

    pass_rate: float = 0.0

    status: str = "GENERATED"


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

    findings: List[QAFinding] = Field(default_factory=list)

    metrics: QAMetrics

    generated_at: datetime = Field(
        default_factory=datetime.utcnow
    )


# ------------------------------------------------------------------
# API Response
# ------------------------------------------------------------------

# class TestingRunResponse(BaseModel):
#     """
#     Response returned after QA Agent execution.
#     """

#     feature_id: str

#     status: str

#     json_report: Optional[str] = None

#     markdown_report: Optional[str] = None

#     generated_tests_path: str

#     generated_files: List[GeneratedTestFile] = Field(
#         default_factory=list
#     )

#     summary: QASummary