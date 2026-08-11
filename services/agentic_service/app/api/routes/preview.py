"""
Live preview routes.

Explicit Start/Stop/Status for a feature's Coder Agent-generated Next.js app,
mirroring agents.py's existing per-feature route scoping style.
"""

from fastapi import APIRouter, HTTPException

from app.services.in_memory_store import store
from app.services.preview_service import (
    PreviewConflictError,
    PreviewNotBuiltError,
    PreviewUnsupportedStackError,
    preview_service,
)

router = APIRouter(tags=["Preview"])


def _require_feature(feature_id: str) -> None:
    if not store.features.get(feature_id):
        raise HTTPException(status_code=404, detail="Feature not found")


@router.post("/features/{feature_id}/preview/start")
def start_preview(feature_id: str):
    _require_feature(feature_id)

    try:
        return preview_service.start_preview(feature_id)
    except PreviewUnsupportedStackError as error:
        raise HTTPException(status_code=400, detail={"reason": "unsupported_stack", "message": str(error)})
    except PreviewNotBuiltError as error:
        raise HTTPException(status_code=409, detail={"reason": "not_built", "message": str(error)})
    except PreviewConflictError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "conflict",
                "message": str(error),
                "conflicting_feature_id": error.conflicting_feature_id,
                "conflicting_feature_name": error.conflicting_feature_name,
            },
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/features/{feature_id}/preview/status")
def get_preview_status(feature_id: str):
    _require_feature(feature_id)

    return preview_service.get_status(feature_id)


@router.post("/features/{feature_id}/preview/stop")
def stop_preview(feature_id: str):
    _require_feature(feature_id)

    preview_service.stop_preview(feature_id)

    return {"status": "stopped"}
