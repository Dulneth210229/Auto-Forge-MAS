"""
Security Agent internal schemas.

Real shapes, replacing the earlier placeholder that always returned
status="skipped". Mirrors the input convention every other agent already
uses (feature_id resolved to project via the shared store), and keeps a
report-shaped output so this agent still slots into the same
artifact-saving path (artifact_service.save_json_artifact /
save_text_artifact) as every implemented agent before it.
"""

from pydantic import BaseModel


class SecurityAgentInput(BaseModel):
    feature_id: str


class SecurityFinding(BaseModel):
    id: str
    rule_id: str
    layer: str  # "pattern" | "secret" | "dependency"
    severity: str  # "critical" | "high" | "medium" | "low" | "unknown"
    cwe: str
    file: str
    line: int | None = None
    message: str


class SecurityAgentOutput(BaseModel):
    security_report_json: dict = {}
    status: str = "completed"
    gate_decision: str = "pass"  # "pass" | "fail"
    findings_count: int = 0
    critical_or_high_count: int = 0
    artifact_ids: list[str] = []
    message: str = ""
