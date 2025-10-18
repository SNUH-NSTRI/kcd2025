"""Workspace data access endpoints."""

from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from rwe_api.config import settings  # Centralized config
from rwe_api.schemas.workspace import WorkspaceDataResponse
from rwe_api.services import WorkspaceService

router = APIRouter()

# Use centralized config (ALWAYS loads .env)
workspace_service = WorkspaceService(settings.WORKSPACE_ROOT)


@router.get("/{project_id}/{stage}", response_model=WorkspaceDataResponse)
async def get_stage_data(project_id: str, stage: str):
    """Get workspace data for a specific project stage."""
    try:
        result = workspace_service.get_project_stage_data(project_id, stage)
        return WorkspaceDataResponse(**result, data=None)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/{stage}/{filename:path}")
async def get_file_content(project_id: str, stage: str, filename: str):
    """Read a specific file from workspace."""
    try:
        result = workspace_service.read_file(project_id, stage, filename)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/corpus")
async def get_corpus(project_id: str):
    """Get literature corpus for a project."""
    try:
        return workspace_service.get_corpus(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/schema")
async def get_schema(project_id: str):
    """Get trial schema for a project."""
    try:
        return workspace_service.get_schema(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/filter-spec")
async def get_filter_spec(project_id: str):
    """Get filter specification for a project."""
    try:
        return workspace_service.get_filter_spec(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/cohort")
async def get_cohort(project_id: str):
    """Get cohort data for a project."""
    try:
        return workspace_service.get_cohort(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/cohort-summary")
async def get_cohort_summary(project_id: str):
    """Get cohort summary for a project."""
    try:
        return workspace_service.get_cohort_summary(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/analysis")
async def get_analysis(project_id: str):
    """Get analysis results for a project."""
    try:
        return workspace_service.get_analysis(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/report")
async def get_report(project_id: str):
    """Get report for a project."""
    try:
        return workspace_service.get_report(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outputs")
async def get_output_file(path: str = Query(..., description="Full path to the output file")):
    """
    Serve static output files (images, markdown, etc.) from the workspace.

    This endpoint allows the frontend to fetch generated artifacts like:
    - Kaplan-Meier plots (PNG)
    - Love plots / SMD plots (PNG)
    - Baseline characteristics tables (MD)

    Security:
    - Path must be within WORKSPACE_ROOT
    - No directory traversal allowed

    Args:
        path: Full path to the file (e.g., "project/NCT03389555/cohorts/med/outputs/main_analysis_smd_plot.png")

    Returns:
        FileResponse: The requested file with appropriate content type

    Raises:
        HTTPException: 400 if path is invalid, 404 if file not found
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[GET /api/workspace/outputs] Requested path: {path}")

    try:
        # Resolve the full path
        full_path = Path(path)
        logger.info(f"[GET /api/workspace/outputs] Full path object: {full_path}")

        # If path is relative, resolve it relative to WORKSPACE_ROOT
        if not full_path.is_absolute():
            full_path = settings.WORKSPACE_ROOT / full_path

        # Security check: Ensure the path is within WORKSPACE_ROOT
        resolved_path = full_path.resolve()
        workspace_root = settings.WORKSPACE_ROOT.resolve()

        if not str(resolved_path).startswith(str(workspace_root)):
            raise HTTPException(
                status_code=400,
                detail="Access denied: Path must be within workspace root"
            )

        # Check if file exists
        if not resolved_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {path}"
            )

        if not resolved_path.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a file: {path}"
            )

        # Determine media type based on file extension
        media_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".json": "application/json",
        }

        media_type = media_type_map.get(resolved_path.suffix.lower(), "application/octet-stream")

        return FileResponse(
            path=resolved_path,
            media_type=media_type,
            filename=resolved_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")

