"""
Smart Complaint Management System
FastAPI application factory and entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.logging_config import get_logger, setup_logging

# Initialize logging first
setup_logging()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: runs on startup and shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    settings = get_settings()
    logger.info(
        "Starting %s v%s [%s]",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )

    # Import all models so Base.metadata knows about every table
    import app.models  # noqa: F401

    # Create tables (Alembic migrations are also available)
    init_db()

    # Start background escalation scheduler
    from app.services.scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()

    yield  # Application is running

    shutdown_scheduler()
    logger.info("Shutting down %s", settings.app_name)


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Smart Complaint Management System for Colleges and Institutions. "
            "Supports complaint creation, tracking, assignment, resolution, "
            "analytics, and AI-powered features."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global Exception Handler ──────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred.",
                "type": type(exc).__name__,
            },
        )

    # ── Register Routers ──────────────────────────────────────────────────
    from app.api.v1.health import router as health_router
    from app.api.v1.auth import router as auth_router
    from app.api.v1.complaints import router as complaints_router
    from app.api.v1.escalation import router as escalation_router
    from app.api.v1.analytics import router as analytics_router

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(complaints_router)
    app.include_router(escalation_router)
    app.include_router(analytics_router)

    # ── Serve Frontend ────────────────────────────────────────────────────
    import os
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if os.path.isdir(frontend_path):
        app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")

    # ── Root Redirect ─────────────────────────────────────────────────────
    @app.get("/", tags=["Root"], summary="API root")
    def root():
        # Return a JSON root payload for health checks and CI
        return JSONResponse(
            status_code=200,
            content={
                "message": f"{settings.app_name} is running",
                "version": settings.app_version,
                "docs": "/docs",
            },
        )

    logger.info("Application created successfully.")
    return app


# Create the app instance
app = create_app()


# ---------------------------------------------------------------------------
# Direct execution support
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
    )
