"""
Summary Generation API Routes

Provides endpoints to generate LLM-based summaries from existing analysis results.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rwe_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/summary", tags=["summary"])


class SummaryRequest(BaseModel):
    """Request to generate summary from existing analysis."""
    nct_id: str = Field(..., description="NCT trial ID")
    medication: str = Field(..., description="Medication name")


class SummaryResponse(BaseModel):
    """Response with generated summary."""
    summary: Dict[str, Any] = Field(..., description="LLM-generated summary")
    source: str = Field(..., description="Source file path")


@router.post("/generate", response_model=SummaryResponse)
async def generate_summary_from_analysis(request: SummaryRequest):
    """
    Load pre-generated LLM summary from analysis workflow.

    Reads llm_summary.json that was generated during the statistician workflow.

    Args:
        request: SummaryRequest with nct_id and medication

    Returns:
        SummaryResponse with generated summary

    Raises:
        HTTPException: If summary file not found
    """
    try:
        # Construct path to llm_summary.json
        # WORKSPACE_ROOT = /Users/kyh/Workspace/datathon_20251017/project
        # Final path: {WORKSPACE_ROOT}/{nct_id}/cohorts/{medication}/analysis_output/llm_summary.json
        cohort_dir = (
            Path(settings.WORKSPACE_ROOT) /
            request.nct_id /
            "cohorts" /
            request.medication
        )

        llm_summary_file = cohort_dir / "analysis_output" / "llm_summary.json"

        logger.info(f"Looking for LLM summary file: {llm_summary_file}")

        if not llm_summary_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"LLM summary not found: {llm_summary_file}. Please run the Statistician analysis first."
            )

        # Load pre-generated LLM summary
        with open(llm_summary_file, 'r') as f:
            llm_summary = json.load(f)

        logger.info(f"Loaded pre-generated LLM summary from {llm_summary_file}")

        return SummaryResponse(
            summary=llm_summary,
            source=str(llm_summary_file)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )
