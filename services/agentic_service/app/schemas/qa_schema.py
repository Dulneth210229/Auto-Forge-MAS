from pydantic import BaseModel, Field


class QAAgentRunRequest(BaseModel):
    human_comment: str | None = None
    approved_security_artifact_id: str | None = None


class QAAgentReviseRequest(BaseModel):
    revision_comment: str = Field(..., min_length=1)
    revised_by: str | None = None