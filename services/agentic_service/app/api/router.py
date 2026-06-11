"""
Main API router.

This file combines all route files into one router.
Then main.py includes this router.
"""

from fastapi import APIRouter

from app.api.routes import (
    health,
    projects,
    features,
    artifacts,
    approvals,
    agents,
    llm_settings,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(features.router)
api_router.include_router(artifacts.router)
api_router.include_router(approvals.router)
api_router.include_router(agents.router)
api_router.include_router(llm_settings.router)