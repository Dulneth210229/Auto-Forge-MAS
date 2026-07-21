"""
FastAPI endpoints for the QA Agent.
"""

from fastapi import APIRouter, HTTPException, status

from app.agents.qa_agent.agent import qa_agent
from app.agents.qa_agent.schemas import TestingRunRequest
from app.schemas.agent_schema import AgentRunResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/features",
    tags=["QA Agent"],
)


@router.post(
    "/{feature_id}/agents/qa/run",
    response_model=AgentRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run QA Agent",
    description="Generate QA test cases for a feature.",
)
async def run_qa_agent(
    feature_id: str,
    request: TestingRunRequest,
) -> AgentRunResponse:
    """
    Execute the QA Agent workflow.
    """

    logger.info(
        "Received QA Agent request for feature_id=%s",
        feature_id,
    )

    try:

        response = await qa_agent.run(
            feature_id=feature_id,
            request=request,
        )

        logger.info(
            "QA Agent completed successfully for feature_id=%s",
            feature_id,
        )

        return response

    except FileNotFoundError as exc:

        logger.error(str(exc))

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        logger.error(str(exc))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Unexpected QA Agent error."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="QA Agent execution failed.",
        ) from exc