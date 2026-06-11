"""
FastAPI application entry point.

Run this backend using:

    uvicorn app.main:app --reload

This file:
- creates the FastAPI app
- registers routes
- enables basic startup checks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend for Human-in-the-Loop Multi-Agent SDLC Automation System"
)

# CORS is enabled for local frontend development.
# Later, restrict origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """
    Root endpoint.
    """
    return {
        "message": "AutoForge Agentic SDLC Backend is running",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# Register all API routes with version prefix.
app.include_router(api_router, prefix=settings.API_PREFIX)