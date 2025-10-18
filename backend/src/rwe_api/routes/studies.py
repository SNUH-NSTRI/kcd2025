"""Study management endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from rwe_api.config import settings  # Centralized config
from rwe_api.schemas.studies import (
    CreateStudyRequest,
    StudyResponse,
    StudyStatus,
)
from rwe_api.services.pipeline_service import PipelineService
from rwe_api.services.study_service import StudyService

router = APIRouter()

# Use centralized config (ALWAYS loads .env)
pipeline_service = PipelineService(settings.WORKSPACE_ROOT)
study_service = StudyService(settings.WORKSPACE_ROOT, pipeline_service)


@router.post("/studies", response_model=StudyResponse)
async def create_study(request: CreateStudyRequest):
    """Create a new study and start background processing.

    This endpoint:
    1. Creates a study directory structure
    2. Saves study metadata
    3. Starts background pipeline (search-lit + parse-trials)
    4. Returns immediately with study ID

    The client should poll /studies/{study_id}/status to track progress.

    Args:
        request: Study creation parameters

    Returns:
        StudyResponse with generated study_id

    Example:
        POST /api/studies
        {
            "name": "Hydrocortisone in Severe Sepsis Study",
            "nct_id": "NCT03389555",
            "research_question": "Effect of hydrocortisone on mortality in septic shock",
            "medicine_family": "Corticosteroids",
            "medicine_generic": "Hydrocortisone",
            "medicine_brand": "Solu-Cortef"
        }

        Response:
        {
            "status": "success",
            "message": "Study created and processing started",
            "study_id": "NCT03389555_20251015203000"
        }
    """
    try:
        study_id = await study_service.create_study(request)

        return StudyResponse(
            status="success",
            message=f"Study created and processing started",
            study_id=study_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/studies/{study_id}/status", response_model=StudyStatus)
async def get_study_status(study_id: str):
    """Get current processing status of a study.

    This endpoint should be polled (e.g., every 3 seconds) to track
    the progress of background pipeline execution.

    Args:
        study_id: Study identifier

    Returns:
        StudyStatus with current step progress

    Example:
        GET /api/studies/NCT03389555_20251015203000/status

        Response:
        {
            "study_id": "NCT03389555_20251015203000",
            "overall_status": "processing",
            "current_step": "schema_parsing",
            "steps": [
                {
                    "step": "corpus",
                    "label": "Fetching trial from ClinicalTrials.gov",
                    "status": "done",
                    "started_at": "2025-10-15T20:30:05",
                    "completed_at": "2025-10-15T20:30:12"
                },
                {
                    "step": "schema_parsing",
                    "label": "Analyzing eligibility criteria with LLM",
                    "status": "in_progress",
                    "started_at": "2025-10-15T20:30:13",
                    "completed_at": null
                },
                ...
            ],
            "created_at": "2025-10-15T20:30:00",
            "updated_at": "2025-10-15T20:30:15",
            "error": null
        }
    """
    try:
        return await study_service.get_study_status(study_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/studies/{study_id}/corpus")
async def get_study_corpus(study_id: str):
    """Get corpus data for a study.

    Returns the trial data fetched from ClinicalTrials.gov,
    including original eligibility criteria text.

    Args:
        study_id: Study identifier

    Returns:
        Corpus data (LiteratureCorpus JSON)

    Example:
        GET /api/studies/NCT03389555_20251015203000/corpus

        Response:
        {
            "documents": [
                {
                    "title": "Hydrocortisone Plus Fludrocortisone for Adults With Septic Shock",
                    "metadata": {
                        "nct_id": "NCT03389555",
                        "eligibility": {
                            "eligibilityCriteria": "Inclusion Criteria:\\n- Age >= 18 years\\n..."
                        },
                        ...
                    }
                }
            ]
        }
    """
    try:
        return await study_service.get_corpus(study_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Corpus not found for study {study_id}. "
            "It may still be processing or the study doesn't exist.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/studies/{study_id}/schema")
async def get_study_schema(study_id: str):
    """Get schema data for a study.

    Returns the parsed trial schema including inclusion/exclusion
    criteria and MIMIC-IV feature mappings.

    Args:
        study_id: Study identifier

    Returns:
        Schema data (TrialSchema JSON)

    Example:
        GET /api/studies/NCT03389555_20251015203000/schema

        Response:
        {
            "schema_version": "trial.v1",
            "inclusion": [
                {
                    "id": "inc_age_18",
                    "description": "Age >= 18 years",
                    "category": "demographic",
                    "kind": "age_range",
                    "value": {
                        "field": "age",
                        "op": ">=",
                        "value": 18
                    }
                },
                ...
            ],
            "exclusion": [...],
            "features": [...]
        }
    """
    try:
        return await study_service.get_schema(study_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Schema not found for study {study_id}. "
            "Parsing may still be in progress, check /studies/{study_id}/status",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/studies/{study_id}/retry")
async def retry_study_parsing(study_id: str):
    """Retry schema parsing for a failed study.

    Use this endpoint when schema parsing fails and you want to retry.

    Args:
        study_id: Study identifier

    Returns:
        Success message

    Example:
        POST /api/studies/NCT03389555_20251015203000/retry

        Response:
        {
            "status": "success",
            "message": "Parsing retry initiated"
        }
    """
    try:
        await study_service.retry_parsing(study_id)
        return {"status": "success", "message": "Parsing retry initiated"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
