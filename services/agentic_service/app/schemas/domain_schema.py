"""
Domain Agent API schemas.

The Domain Agent enhances the latest approved SRS using domain knowledge
retrieved (RAG) from files under settings.DOMAIN_KNOWLEDGE_BASE_DIR, and
produces:
- Enhanced SRS Markdown
- Enhanced SRS JSON
- Domain Improvements JSON (what was added/changed, and why)
"""

from pydantic import BaseModel, Field


class DomainAgentRunRequest(BaseModel):
    """
    Request body for running the Domain Agent.

    There is no approved_srs_artifact_id field here -- like Architecture
    Agent, DomainAgent looks up the latest APPROVED SRS JSON artifact for
    this feature itself.
    """

    human_comment: str | None = Field(
        default=None,
        example="Focus on payment and inventory domain rules.",
    )


class DomainAgentReviseRequest(BaseModel):
    """
    Request body for revising the latest Enhanced SRS.
    """

    revision_comment: str = Field(
        ...,
        example="Add PCI-DSS tokenization requirement explicitly.",
    )

    revised_by: str = Field(default="human_user", example="human_user")
