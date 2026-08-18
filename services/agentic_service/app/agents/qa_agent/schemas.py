"""
QA Agent internal schemas.

Real shapes, replacing the earlier placeholder that always returned
status="skipped".
"""

from pydantic import BaseModel


class QAAgentInput(BaseModel):
    feature_id: str


class QATestResult(BaseModel):
    file: str
    passed: int
    failed: int
    skipped: int


class QAAgentOutput(BaseModel):
    qa_report_json: dict = {}
    status: str = "completed"
    framework_used: str = ""
    tests_generated: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    artifact_ids: list[str] = []
    message: str = ""
