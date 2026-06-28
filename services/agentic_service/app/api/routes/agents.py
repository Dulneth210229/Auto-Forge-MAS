"""
Agent routes.

Implemented agents:
- RequirementAgent  (/requirement/run)
- ArchitectureAgent (/architecture/run)
- CoderAgent        (/coder/run)  ← production implementation

Placeholder agents (to be implemented):
- DomainAgent
- UIUXAgent
- DeploymentAgent
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

# Coder Agent imports
from app.agents.coder_agent.agent import CoderAgent
from app.agents.coder_agent.schemas import CoderAgentInput
from app.agents.coder_agent.env_validator import MissingEnvVarsError
from app.schemas.coder_schema import CoderAgentRunRequest
from app.schemas.approval_schema import ApprovalRequest
from app.utils.logger import get_logger
from app.services.approval_service import approval_service

_coder_route_logger = get_logger("api.routes.agents.coder")

router = APIRouter(prefix="/features/{feature_id}/agents", tags=["Agents"])


def _validate_feature(feature_id: str):
    """
    Helper function to check whether a feature exists.
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return feature


def _get_project_for_feature(feature: dict) -> dict:
    """
    Helper function to retrieve the project that owns a given feature.

    Raises HTTP 404 if the parent project cannot be found.
    """
    project_id = feature.get("project_id")
    project = store.projects.get(project_id)

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project not found for feature (project_id={project_id})."
        )

    return project


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
    # UI/UX Agent
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
async def run_coder_agent(
    feature_id: str,
    request: CoderAgentRunRequest = Body(default_factory=CoderAgentRunRequest)
):
    """
    Run the Coder Agent for the approved feature.

    Approval gates (all must pass):
    1. Approved SRS Markdown artifact (from Requirement Agent).
    2. Approved Enhanced SRS Markdown artifact (from Domain Agent).
    3. Approved SDS Markdown artifact (from Architecture Agent).
    4. All required environment variables declared in request.env_vars.

    This endpoint:
    - Loads all approved artifact content from disk.
    - Loads the previous project snapshot (for iterative merging).
    - Validates required environment variables against the SDS.
    - Builds the generation prompt with minimal context.
    - Calls the configured LLM provider.
    - Parses and validates the LLM response.
    - Merges new/updated files with the existing project snapshot.
    - Saves 5 versioned artifacts: file_tree, code_manifest,
      setup_instructions, merge_report, requirement_code_map.
    - Returns artifact IDs for the human approval workflow.
    """
    feature = _validate_feature(feature_id)
    project = _get_project_for_feature(feature)

    _coder_route_logger.info(
        "[CoderRoute] /coder/run called. feature_id=%s project_id=%s",
        feature_id, project["project_id"]
    )

    # ----------------------------------------------------------------
    # Gate 1: Approved SRS
    # ----------------------------------------------------------------
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
                "Coder Agent cannot run: approved SRS Markdown artifact is missing. "
                "Approve the Requirement Agent output first."
            )
        )

    # ----------------------------------------------------------------
    # Gate 2: Approved Enhanced SRS
    # ----------------------------------------------------------------
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
                "Coder Agent cannot run: approved Enhanced SRS Markdown artifact is missing. "
                "Approve the Domain Agent output first."
            )
        )

    # ----------------------------------------------------------------
    # Gate 3: Approved SDS
    # ----------------------------------------------------------------
    approved_sds = artifact_service.get_latest_approved_artifact(
        feature_id=feature_id,
        agent_name=AgentName.ARCHITECTURE,
        artifact_type=ArtifactType.SDS,
        artifact_format=ArtifactFormat.MARKDOWN
    )
    if not approved_sds:
        raise HTTPException(
            status_code=400,
            detail=(
                "Coder Agent cannot run: approved SDS Markdown artifact is missing. "
                "Approve the Architecture Agent output first."
            )
        )

    # ----------------------------------------------------------------
    # Load artifact content from disk
    # ----------------------------------------------------------------
    try:
        srs_markdown = artifact_service.read_artifact_content(approved_srs.artifact_id)
        enhanced_srs_markdown = artifact_service.read_artifact_content(
            approved_enhanced_srs.artifact_id
        )
        sds_markdown = artifact_service.read_artifact_content(approved_sds.artifact_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read approved artifact content: {exc}"
        )

    # ----------------------------------------------------------------
    # Optional: Load approved UI Design (non-blocking)
    # ----------------------------------------------------------------
    ui_design_html: str | None = None
    if not request.skip_uiux:
        approved_ui = artifact_service.get_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.UIUX,
            artifact_type=ArtifactType.UI_DESIGN,
            artifact_format=ArtifactFormat.HTML
        )
        if approved_ui:
            try:
                ui_design_html = artifact_service.read_artifact_content(
                    approved_ui.artifact_id
                )
            except Exception:
                _coder_route_logger.warning(
                    "[CoderRoute] Could not read UI Design artifact (non-blocking)."
                )

    # ----------------------------------------------------------------
    # Assemble CoderAgentInput
    # ----------------------------------------------------------------
    agent_input = CoderAgentInput(
        project_id=project["project_id"],
        project_name=project["project_name"],
        project_type=project["project_type"],
        target_stack=project["target_stack"],
        feature_id=feature_id,
        feature_name=feature["feature_name"],
        approved_srs_markdown=srs_markdown,
        approved_enhanced_srs_markdown=enhanced_srs_markdown,
        approved_sds_markdown=sds_markdown,
        approved_ui_design_html=ui_design_html,
        # previous_project_snapshot is loaded inside the agent (Step 2)
        previous_project_snapshot=[],
        previous_feature_names=[],
        env_vars_provided=request.env_vars,
        coding_standards=request.coding_standards,
        human_comment=request.human_comment,
    )

    # ----------------------------------------------------------------
    # Run Coder Agent
    # ----------------------------------------------------------------
    try:
        coder_agent = CoderAgent()
        output = await coder_agent.run(agent_input)

    except MissingEnvVarsError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_env_vars",
                "message": str(exc),
                "missing_vars": exc.missing_vars,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Coder Agent runtime error: {exc}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Coder Agent unexpected error: {exc}"
        )

    # ----------------------------------------------------------------
    # Save artifacts
    # ----------------------------------------------------------------
    generated_artifact_ids: list[str] = []

    try:
        # Determine shared version for this run
        run_version = output.artifact_metadata.version

        # --- 1. File Tree JSON ---
        file_tree_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE,
            filename="file_tree_v{version}.json",
            data=output.file_tree,
            version_override=run_version,
        )
        generated_artifact_ids.append(file_tree_artifact.artifact_id)

        # --- 2. Code Manifest JSON (full snapshot) ---
        code_manifest_data = {
            "artifact_metadata": output.artifact_metadata.model_dump(),
            "generated_files": [f.model_dump() for f in output.generated_files],
            "updated_files": [f.model_dump() for f in output.updated_files],
            "unchanged_files": [f.model_dump() for f in output.unchanged_files],
            "env_vars_required": [v.model_dump() for v in output.env_vars_required],
            "run_commands": output.run_commands,
            "integration_notes": output.integration_notes,
            "previous_feature_names": (
                agent_input.previous_feature_names + [feature["feature_name"]]
            ),
        }
        code_manifest_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE,
            filename="code_manifest_v{version}.json",
            data=code_manifest_data,
            version_override=run_version,
        )
        generated_artifact_ids.append(code_manifest_artifact.artifact_id)

        # --- 3. Requirement-to-Code Mapping JSON ---
        req_map_data = {
            "feature_id": feature_id,
            "feature_name": feature["feature_name"],
            "version": run_version,
            "mappings": [m.model_dump() for m in output.requirement_mapping],
        }
        req_map_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE,
            filename="requirement_code_map_v{version}.json",
            data=req_map_data,
            version_override=run_version,
        )
        generated_artifact_ids.append(req_map_artifact.artifact_id)

        # --- 4. Setup Instructions Markdown ---
        setup_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename="setup_instructions_v{version}.md",
            content=output.setup_instructions_markdown,
            version_override=run_version,
        )
        generated_artifact_ids.append(setup_artifact.artifact_id)

        # --- 5. Merge Report Markdown ---
        merge_report_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename="merge_report_v{version}.md",
            content=output.merge_report_markdown,
            version_override=run_version,
        )
        generated_artifact_ids.append(merge_report_artifact.artifact_id)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Coder Agent: failed to save artifacts: {exc}"
        )

    # ----------------------------------------------------------------
    # Update feature current agent
    # ----------------------------------------------------------------
    feature["current_agent"] = AgentName.CODER

    _coder_route_logger.info(
        "[CoderRoute] Coder Agent completed. feature_id=%s artifacts=%d "
        "new_files=%d updated_files=%d unchanged_files=%d",
        feature_id,
        len(generated_artifact_ids),
        len(output.generated_files),
        len(output.updated_files),
        len(output.unchanged_files),
    )

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.CODER,
        status="completed",
        message=(
            f"Coder Agent completed successfully for feature '{feature['feature_name']}'. "
            f"Generated {len(output.generated_files)} new files, "
            f"updated {len(output.updated_files)} files, "
            f"preserved {len(output.unchanged_files)} unchanged files."
        ),
        artifact_ids=generated_artifact_ids,
    )


@router.post("/coder/seed-prereqs")
async def seed_coder_prerequisites(feature_id: str):
    """
    Create dummy approved prerequisites for local coder testing.

    This helper seeds only the two missing gates required by the coder route:
    - approved Enhanced SRS Markdown
    - approved SDS Markdown

    It does not implement the Domain Agent.
    """
    feature = _validate_feature(feature_id)
    project = _get_project_for_feature(feature)

    approved_srs = artifact_service.get_latest_approved_artifact(
        feature_id=feature_id,
        agent_name=AgentName.REQUIREMENT,
        artifact_type=ArtifactType.SRS,
        artifact_format=ArtifactFormat.MARKDOWN,
    )

    if not approved_srs:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot seed coder prerequisites because approved Requirement SRS "
                "Markdown artifact is missing. Approve Requirement Agent output first."
            ),
        )

    srs_content = artifact_service.read_artifact_content(approved_srs.artifact_id)

    enhanced_srs_content = (
        f"# Enhanced SRS: {feature['feature_name']}\n\n"
        "This is a dummy Enhanced SRS placeholder created for local coder testing.\n\n"
        "## Source Requirement Summary\n\n"
        f"{srs_content}\n"
    )

    sds_content = (
        f"# Software Design Specification: {feature['feature_name']}\n\n"
        "This is a dummy SDS placeholder created for local coder testing.\n\n"
        "## Architecture Summary\n\n"
        f"- Project: {project['project_name']}\n"
        f"- Feature: {feature['feature_name']}\n"
        f"- Target Stack: {project['target_stack']}\n\n"
        "## Notes\n\n"
        "- This SDS intentionally omits required environment variables so the "
        "coder agent can be exercised locally without additional gating.\n"
    )

    enhanced_artifact = artifact_service.save_text_artifact(
        project=project,
        feature=feature,
        agent_name=AgentName.DOMAIN,
        artifact_type=ArtifactType.ENHANCED_SRS,
        artifact_format=ArtifactFormat.MARKDOWN,
        filename="Enhanced_SRS_v{version}.md",
        content=enhanced_srs_content,
    )
    approval_service.submit_approval(
        artifact_id=enhanced_artifact.artifact_id,
        request=ApprovalRequest(
            status="approved",
            reviewer_comment="Seeded dummy Enhanced SRS for coder testing.",
            approved_by="system",
        ),
    )

    sds_artifact = artifact_service.save_text_artifact(
        project=project,
        feature=feature,
        agent_name=AgentName.ARCHITECTURE,
        artifact_type=ArtifactType.SDS,
        artifact_format=ArtifactFormat.MARKDOWN,
        filename="SDS_v{version}.md",
        content=sds_content,
    )
    approval_service.submit_approval(
        artifact_id=sds_artifact.artifact_id,
        request=ApprovalRequest(
            status="approved",
            reviewer_comment="Seeded dummy SDS for coder testing.",
            approved_by="system",
        ),
    )

    return {
        "feature_id": feature_id,
        "message": "Dummy Enhanced SRS and SDS artifacts were created and approved.",
        "artifact_ids": [enhanced_artifact.artifact_id, sds_artifact.artifact_id],
    }


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