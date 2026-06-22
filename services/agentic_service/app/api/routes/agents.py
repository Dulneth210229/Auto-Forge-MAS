"""
Agent routes.

For now, this file contains placeholder endpoints.

Later, each endpoint will call the real agent class:
- RequirementAgent
- DomainAgent
- ArchitectureAgent
- UIUXAgent
- CoderAgent
- DeploymentAgent

At this foundation step, we only verify the API structure.
"""

from fastapi import APIRouter, HTTPException, Body

from app.core.enums import AgentName
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.in_memory_store import store
from app.agents.requirement_agent.agent import requirement_agent
from app.agents.architecture_agent.agent import ArchitectureAgent
from app.agents.architecture_agent.schemas import ArchitectureAgentInput
from app.core.enums import AgentName, ArtifactType, ArtifactFormat
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.artifact_service import artifact_service
from app.schemas.requirement_schema import RequirementAgentRunRequest
from app.services.in_memory_store import store
from app.services.plantuml_service import plantuml_service
from app.utils.file_manager import read_json_file

router = APIRouter(prefix="/features/{feature_id}/agents", tags=["Agents"])


def _validate_feature(feature_id: str):
    """
    Helper function to check whether a feature exists.
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return feature


@router.post("/requirement/run", response_model=AgentRunResponse)
async def run_requirement_agent(
    feature_id: str,
    request: RequirementAgentRunRequest
):
    """
    Run the Requirement Agent.

    This endpoint:
    - receives structured BA input
    - supports architectural_style input
    - calls the selected LLM provider
    - generates SRS Markdown and SRS JSON
    - saves both files as artifacts
    - returns artifact IDs

    Human approval is required after this.
    """
    _validate_feature(feature_id)

    try:
        return await requirement_agent.run(
            feature_id=feature_id,
            request=request
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Requirement Agent failed: {str(error)}"
        )


@router.post("/domain/run", response_model=AgentRunResponse)
async def run_domain_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Domain Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.DOMAIN,
        status="not_implemented_yet",
        message="Domain Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )

  # ----------------------------------------------------
# Architecture Agent
# ----------------------------------------------------

def _get_project_for_feature(feature: dict):
    """
    Get the project related to the selected feature.

    Why this helper is needed:
    - The Architecture Agent needs project context.
    - Example: project_type, target_stack, project_name.
    - Feature only stores project_id, so we use that to find the project.
    """
    project = store.projects.get(feature["project_id"])

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.post("/architecture/run", response_model=AgentRunResponse)
async def run_architecture_agent(
    feature_id: str,
    request: AgentRunRequest = Body(default=AgentRunRequest())
):
    """
    Run the Architecture Agent.

    This updated version uses JSON artifacts as input, not Markdown.

    Required approved inputs:
    1. Requirement Agent output:
       - SRS_v1.json
       - artifact_type = srs
       - artifact_format = json
       - approval_status = approved

    2. Domain Agent output:
       - Enhanced_SRS_v1.json
       - artifact_type = enhanced_srs
       - artifact_format = json
       - approval_status = approved

    Architecture Agent output:
    - SDS_v1.md
    - SDS_v1.json
    - usecase_v1.puml
    - usecase_v1.png
    - traceability_architecture_v1.json

    Important:
    - This endpoint does NOT use SRS Markdown as input.
    - This endpoint does NOT generate API contract.
    - This endpoint does NOT generate OpenAPI YAML.
    """

    # ----------------------------------------------------
    # 1. Validate feature and project
    # ----------------------------------------------------
    feature = _validate_feature(feature_id)
    project = _get_project_for_feature(feature)

    # ----------------------------------------------------
    # 2. Load approved SRS JSON from Requirement Agent
    # ----------------------------------------------------
    approved_srs = artifact_service.get_latest_approved_artifact(
        feature_id=feature_id,
        agent_name=AgentName.REQUIREMENT,
        artifact_type=ArtifactType.SRS,
        artifact_format=ArtifactFormat.JSON
    )

    if not approved_srs:
        raise HTTPException(
            status_code=400,
            detail=(
                "Architecture Agent cannot run because approved SRS JSON "
                "artifact is missing. Approve Requirement Agent SRS JSON first."
            )
        )

    # ----------------------------------------------------
    # 3. Load approved Enhanced SRS JSON from Domain Agent
    # ----------------------------------------------------
    approved_enhanced_srs = artifact_service.get_latest_approved_artifact(
        feature_id=feature_id,
        agent_name=AgentName.DOMAIN,
        artifact_type=ArtifactType.ENHANCED_SRS,
        artifact_format=ArtifactFormat.JSON
    )

    if not approved_enhanced_srs:
        raise HTTPException(
            status_code=400,
            detail=(
                "Architecture Agent cannot run because approved Enhanced SRS JSON "
                "artifact is missing. Approve Domain Agent Enhanced SRS JSON first."
            )
        )

    try:
        # ----------------------------------------------------
        # 4. Read JSON artifact file contents
        # ----------------------------------------------------
        # read_json_file() returns Python dict.
        # This is better than Markdown because JSON contains stable IDs:
        # FR-001, NFR-001, AC-001, BR-001, etc.
        srs_json = read_json_file(approved_srs.file_path)

        enhanced_srs_json = read_json_file(
            approved_enhanced_srs.file_path
        )

        # ----------------------------------------------------
        # 5. Prepare Architecture Agent input
        # ----------------------------------------------------
        # IMPORTANT:
        # This input now passes JSON, not Markdown.
        agent_input = ArchitectureAgentInput(
            project_id=project["project_id"],
            feature_id=feature_id,
            approved_srs_json=srs_json,
            approved_enhanced_srs_json=enhanced_srs_json,
            project_type=project["project_type"],
            feature_name=feature["feature_name"],
            target_stack=project["target_stack"],
            human_comment=request.human_comment
        )

        # ----------------------------------------------------
        # 6. Run Architecture Agent
        # ----------------------------------------------------
        architecture_agent = ArchitectureAgent()
        output = await architecture_agent.run(agent_input)

        generated_artifact_ids: list[str] = []

        # ----------------------------------------------------
        # 7. Save SDS Markdown
        # ----------------------------------------------------
        sds_md_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.ARCHITECTURE,
            artifact_type=ArtifactType.SDS,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename="SDS_v{version}.md",
            content=output.sds_markdown
        )
        generated_artifact_ids.append(sds_md_artifact.artifact_id)

        # ----------------------------------------------------
        # 8. Save SDS JSON
        # ----------------------------------------------------
        sds_json_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.ARCHITECTURE,
            artifact_type=ArtifactType.SDS,
            filename="SDS_v{version}.json",
            data=output.sds_json
        )
        generated_artifact_ids.append(sds_json_artifact.artifact_id)

        # ----------------------------------------------------
        # 9. Save PlantUML Use Case Diagram source
        # ----------------------------------------------------
        puml_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.ARCHITECTURE,
            artifact_type=ArtifactType.USE_CASE_DIAGRAM,
            artifact_format=ArtifactFormat.PUML,
            filename="usecase_v{version}.puml",
            content=output.usecase_puml
        )
        generated_artifact_ids.append(puml_artifact.artifact_id)

        # ----------------------------------------------------
        # 10. Render PlantUML to PNG
        # ----------------------------------------------------
        png_path = plantuml_service.render_puml_to_png(
            puml_artifact.file_path
        )

        with open(png_path, "rb") as png_file:
            png_content = png_file.read()

        png_artifact = artifact_service.save_binary_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.ARCHITECTURE,
            artifact_type=ArtifactType.USE_CASE_DIAGRAM,
            artifact_format=ArtifactFormat.PNG,
            filename="usecase_v{version}.png",
            binary_content=png_content
        )
        generated_artifact_ids.append(png_artifact.artifact_id)

        # ----------------------------------------------------
        # 11. Save Architecture Traceability JSON
        # ----------------------------------------------------
        traceability_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.ARCHITECTURE,
            artifact_type=ArtifactType.ARCHITECTURE_TRACEABILITY,
            filename="traceability_architecture_v{version}.json",
            data=output.traceability_json
        )
        generated_artifact_ids.append(traceability_artifact.artifact_id)

        # ----------------------------------------------------
        # 12. Update feature current agent
        # ----------------------------------------------------
        feature["current_agent"] = AgentName.ARCHITECTURE

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.ARCHITECTURE,
            status="completed",
            message=(
                "Architecture Agent completed successfully using approved "
                "SRS JSON and Enhanced SRS JSON. Generated SDS, Use Case Diagram, "
                "and architecture traceability artifacts."
            ),
            artifact_ids=generated_artifact_ids
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Architecture Agent failed: {str(error)}"
        )
    

    # ----------------------------------------------------
    # Ui/UX  Agent
    # ----------------------------------------------------
@router.post("/uiux/run", response_model=AgentRunResponse)
def run_uiux_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for UI/UX Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.UIUX,
        status="not_implemented_yet",
        message="UI/UX Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )


@router.post("/coder/run", response_model=AgentRunResponse)
def run_coder_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Coder Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.CODER,
        status="not_implemented_yet",
        message="Coder Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )


@router.post("/deployment/run", response_model=AgentRunResponse)
def run_deployment_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Deployment Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.DEPLOYMENT,
        status="not_implemented_yet",
        message="Deployment Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )