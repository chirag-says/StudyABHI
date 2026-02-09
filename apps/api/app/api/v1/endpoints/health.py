"""
Health Check Endpoints
System health and status endpoints
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response"""
    status: str
    version: str
    environment: str
    database: str
    redis: str


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    Returns application status and version.
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT
    )


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    Returns 200 if application is running.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    TODO: Add database and Redis connectivity checks.
    """
    # TODO: Check database connection
    # TODO: Check Redis connection
    return {"status": "ready"}
