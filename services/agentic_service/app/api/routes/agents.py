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

from app.agents.architecture_agent.agent import ArchitectureAgent
from app.agents.architecture_agent.schemas import ArchitectureAgentInput
from app.core.enums import AgentName, ArtifactType, ArtifactFormat
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.plantuml_service import plantuml_service

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
def run_requirement_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Requirement Agent.

    Real SRS generation will be added in the next step.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.REQUIREMENT,
        status="not_implemented_yet",
        message="Requirement Agent endpoint is ready. Real logic will be added next.",
        artifact_ids=[]
    )


@router.post("/domain/run", response_model=AgentRunResponse)
def run_domain_agent(feature_id: str, request: AgentRunRequest):
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


@router.post("/architecture/run", response_model=AgentRunResponse)
async def run_architecture_agent(
    feature_id: str,
    request: AgentRunRequest = Body(default=AgentRunRequest())
):
    """
    Run the Architecture Agent.

    This endpoint:
    1. Checks approved SRS.
    2. Checks approved Enhanced SRS.
    3. Runs Architecture Agent.
    4. Saves SDS Markdown.
    5. Saves SDS JSON.
    6. Saves Use Case PlantUML.
    7. Renders Use Case PNG.
    8. Saves traceability JSON.

    Important:
    This endpoint does NOT generate API contract or OpenAPI YAML.
    """

    feature = _validate_feature(feature_id)
    project = _get_project_for_feature(feature)

    # ----------------------------------------------------
    # 1. Load approved SRS from Requirement Agent
    # ----------------------------------------------------
    approved_srs = artifact_service.get_latest_approved_artifact(
        feature_id=feature_id,
        agent_name=AgentName.REQUIREMENT,
        artifact_type=ArtifactType.SRS,
        artifact_format=ArtifactFormat.MARKDOWN
    )

    if not approved_srs:
        raise HTTPException(
            status_code=400,
            detail=(
                "Architecture Agent cannot run because approved SRS Markdown "
                "artifact is missing. Approve Requirement Agent output first."
            )
        )

    # ----------------------------------------------------
    # 2. Load approved Enhanced SRS from Domain Agent
    # ----------------------------------------------------
    approved_enhanced_srs = artifact_service.get_latest_approved_artifact(
        feature_id=feature_id,
        agent_name=AgentName.DOMAIN,
        artifact_type=ArtifactType.ENHANCED_SRS,
        artifact_format=ArtifactFormat.MARKDOWN
    )

    if not approved_enhanced_srs:
        raise HTTPException(
            status_code=400,
            detail=(
                "Architecture Agent cannot run because approved Enhanced SRS "
                "Markdown artifact is missing. Approve Domain Agent output first."
            )
        )

    try:
        srs_markdown = artifact_service.read_artifact_content(
            approved_srs.artifact_id
        )

        enhanced_srs_markdown = artifact_service.read_artifact_content(
            approved_enhanced_srs.artifact_id
        )

        # ----------------------------------------------------
        # 3. Prepare Architecture Agent input
        # ----------------------------------------------------
        agent_input = ArchitectureAgentInput(
            project_id=project["project_id"],
            feature_id=feature_id,
            approved_srs_markdown=srs_markdown,
            approved_enhanced_srs_markdown=enhanced_srs_markdown,
            project_type=project["project_type"],
            feature_name=feature["feature_name"],
            target_stack=project["target_stack"],
            human_comment=request.human_comment
        )

        # ----------------------------------------------------
        # 4. Run Architecture Agent
        # ----------------------------------------------------
        architecture_agent = ArchitectureAgent()
        output = await architecture_agent.run(agent_input)

        generated_artifact_ids: list[str] = []

        # ----------------------------------------------------
        # 5. Save SDS Markdown
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
        # 6. Save SDS JSON
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
        # 7. Save PlantUML source
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
        # 8. Render PNG diagram from PlantUML
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
        # 9. Save Architecture Traceability JSON
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
        # 10. Update feature current agent
        # ----------------------------------------------------
        feature["current_agent"] = AgentName.ARCHITECTURE

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.ARCHITECTURE,
            status="completed",
            message=(
                "Architecture Agent completed successfully. "
                "Generated SDS, Use Case Diagram, and traceability artifacts."
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