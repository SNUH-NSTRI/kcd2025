"""Project management endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from rwe_api.config import settings  # Centralized config
from rwe_api.schemas.workspace import ProjectListResponse, ProjectInfo
from rwe_api.services import WorkspaceService

router = APIRouter()

# Use centralized config (ALWAYS loads .env)
WORKSPACE_ROOT = settings.WORKSPACE_ROOT
PROJECT_ROOT = settings.PROJECT_ROOT
workspace_service = WorkspaceService(WORKSPACE_ROOT)


@router.get("", response_model=ProjectListResponse)
async def list_projects():
    """List all projects in workspace."""
    try:
        projects_data = workspace_service.list_projects()
        projects = [ProjectInfo(**p) for p in projects_data]
        return ProjectListResponse(projects=projects, total=len(projects))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get detailed information about a specific project."""
    try:
        projects = workspace_service.list_projects()
        project = next((p for p in projects if p["project_id"] == project_id), None)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{nct_id}/cohorts/{medication}/data")
async def get_cohort_data(nct_id: str, medication: str):
    """Get cohort CSV data for a specific NCT ID and medication."""
    try:
        # Path pattern: project/{NCT_ID}/cohorts/{medication}/{NCT_ID}_{medication}_v3.1.csv
        cohort_dir = PROJECT_ROOT / nct_id / "cohorts" / medication

        # Try to find the cohort CSV file
        csv_files = list(cohort_dir.glob(f"{nct_id}_{medication}_v*.csv"))

        # Filter out files with "_with_baseline" suffix
        csv_files = [f for f in csv_files if "_with_baseline" not in f.name]

        if not csv_files:
            raise HTTPException(
                status_code=404,
                detail=f"Cohort data not found for {nct_id}/{medication}"
            )

        # Use the most recent version (sorted by name)
        cohort_file = sorted(csv_files)[-1]

        if not cohort_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Cohort file not found: {cohort_file}"
            )

        return FileResponse(
            path=cohort_file,
            media_type="text/csv",
            filename=cohort_file.name
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

