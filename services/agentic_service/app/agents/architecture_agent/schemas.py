"""
Architecture Agent internal schemas.

These schemas are used inside the Architecture Agent only.

Important:
The API request schema is in:
    app/schemas/architecture_schema.py
"""

from pydantic import BaseModel


class ArchitectureAgentInput(BaseModel):
    """
    Internal input passed to Architecture Agent.
    """

    project: dict
    feature: dict
    srs_json: dict
    enhanced_srs_json: dict | None = None
    architecture_notes: str | None = None
    human_comment: str | None = None


class ArchitectureAgentOutput(BaseModel):
    """
    Internal output produced by Architecture Agent.

    The Architecture Agent produces:
    - Architecture Plan Markdown/JSON
    - UML Use Case Diagram JSON/PUML
    - UML Sequence Diagram JSON/PUML
    - UML Class Diagram JSON/PUML

    PNG files are produced when artifacts are saved.
    """

    architecture_plan_json: dict
    architecture_plan_markdown: str

    usecase_analysis_json: dict
    usecase_json: dict
    usecase_puml: str

    sequence_diagram_json: dict
    sequence_puml: str

    class_diagram_json: dict
    class_puml: str

    raw_llm_output: str
