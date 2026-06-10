"""
Shared enum values used across the backend.

Using enums helps us avoid spelling mistakes like:
- "approved"
- "approve"
- "Approval"

All statuses are controlled from one place.
"""

from enum import Enum


class FeatureStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentName(str, Enum):
    REQUIREMENT = "requirement_agent"
    DOMAIN = "domain_agent"
    ARCHITECTURE = "architecture_agent"
    UIUX = "uiux_agent"
    CODER = "coder_agent"
    DEPLOYMENT = "deployment_agent"


class ArtifactType(str, Enum):
    SRS = "srs"
    ENHANCED_SRS = "enhanced_srs"
    SDS = "sds"
    USE_CASE_DIAGRAM = "use_case_diagram"
    UI_DESIGN = "ui_design"
    CODE = "code"
    DEPLOYMENT = "deployment"


class ArtifactFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    TEXT = "text"
    HTML = "html"
    PNG = "png"
    CODE = "code"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"