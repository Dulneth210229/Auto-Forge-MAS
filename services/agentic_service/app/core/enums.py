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

class ArchitectureStyle(str, Enum):
    """
    Preferred architecture style selected by the user or BA.

    Important:
    In Requirement Agent, this is only captured as a requirement/design preference.
    The actual Software Design Specification will be generated later by Architecture Agent.
    """

    MODULAR = "modular"
    MONOLITHIC = "monolithic"
    MVC = "mvc"
    MICROSERVICES = "microservices"
    LAYERED = "layered"
    CLEAN_ARCHITECTURE = "clean_architecture"