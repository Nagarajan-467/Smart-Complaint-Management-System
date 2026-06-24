"""
Health check endpoint for monitoring and readiness probes.
"""

from fastapi import APIRouter

from app.config import get_settings
from app.database import check_db_connection

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health", summary="Application health check")
def health_check():
    """
    Returns the application status and database connectivity.
    Useful for load balancer health probes and monitoring.
    """
    settings = get_settings()
    db_healthy = check_db_connection()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": "connected" if db_healthy else "disconnected",
    }
