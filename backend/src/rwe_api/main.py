"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rwe_api.config import settings  # Centralized config - ALWAYS loads .env
from rwe_api.routes import pipeline, workspace, projects, agents, medicines, studies, cohort, reports, eligibility, trialist, cache, summary
from rwe_api.medicines import initialize_medicines

# Configuration loaded automatically from backend/.env (or project_root/.env as fallback)
# See rwe_api.config for Zen environment loading strategy
CORS_ORIGINS = settings.cors_origins_list
WORKSPACE_ROOT = settings.WORKSPACE_ROOT


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Loads medicine data on startup and cleans up on shutdown.
    """
    # Startup: Load medicine data
    medicines_yaml_path = Path(__file__).parent.parent.parent.parent / "config" / "metadata" / "medicines_variants.yaml"
    print(f"🔄 Loading medicine data from {medicines_yaml_path}")
    initialize_medicines(medicines_yaml_path)

    yield

    # Shutdown: cleanup if needed
    print("👋 Shutting down API")


app = FastAPI(
    title="RWE Clinical Trial Emulation API",
    description="Backend API for Real-World Evidence clinical trial emulation platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(workspace.router, prefix="/api/workspace", tags=["workspace"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(cohort.router, prefix="/api/cohort", tags=["cohort"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(medicines.router)
app.include_router(studies.router, prefix="/api", tags=["studies"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(eligibility.router, prefix="/api/eligibility", tags=["eligibility"])
app.include_router(trialist.router, prefix="/api/trialist", tags=["trialist"])
app.include_router(cache.router, prefix="/api/cache", tags=["cache"])
app.include_router(summary.router)  # Summary generation endpoint


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "RWE Clinical Trial Emulation API",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "workspace_root": str(WORKSPACE_ROOT),
        "workspace_exists": WORKSPACE_ROOT.exists(),
    }

