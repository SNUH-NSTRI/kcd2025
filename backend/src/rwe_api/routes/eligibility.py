"""
Eligibility extraction API endpoints.

This module provides REST API endpoints for the Eligibility Extraction with
Human-in-the-Loop Learning System. It exposes the core extraction and correction
workflow to frontend clients.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from rwe_api.config import settings  # Centralized config
from pipeline import models
from pipeline.context import PipelineContext
from pipeline.plugins import registry
from pipeline.plugins.correction_manager import CorrectionManager
from pipeline.plugins.eligibility_extractor import EligibilityExtractor
from rwe_api.schemas.eligibility_schemas import (
    CorrectionStatsResponse,
    ExtractRequest,
    ExtractResponse,
    ReviewRequest,
    ReviewResponse,
)

router = APIRouter()

# Use centralized config (ALWAYS loads .env)
WORKSPACE_ROOT = settings.WORKSPACE_ROOT
CORRECTIONS_DIR = WORKSPACE_ROOT / "corrections"

# Initialize services (lazy loading to avoid circular imports)
_extractor: EligibilityExtractor | None = None
_correction_manager: CorrectionManager | None = None


def get_extractor() -> EligibilityExtractor:
    """Get or create EligibilityExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = EligibilityExtractor(
            model_name="gpt-4o-mini",
            temperature=0.0,
        )
    return _extractor


def get_correction_manager() -> CorrectionManager:
    """Get or create CorrectionManager instance."""
    global _correction_manager
    if _correction_manager is None:
        _correction_manager = CorrectionManager(corrections_dir=CORRECTIONS_DIR)
    return _correction_manager


@router.post("/extract", response_model=ExtractResponse)
async def extract_eligibility(request: ExtractRequest):
    """
    Extract eligibility criteria from NCT data.

    This endpoint:
    1. Fetches NCT JSON from ClinicalTrials.gov
    2. Selects relevant examples using CorrectionManager
    3. Extracts criteria using EligibilityExtractor with few-shot learning
    4. Returns structured extraction with metadata

    Args:
        request: ExtractRequest containing NCT ID

    Returns:
        ExtractResponse with extraction, examples used, and selection strategy

    Raises:
        HTTPException: If NCT data fetch fails or extraction fails
    """
    try:
        # Step 1: Fetch NCT data from ClinicalTrials.gov
        fetcher = registry.get_literature("langgraph-search")
        ctx = PipelineContext(
            workspace=WORKSPACE_ROOT,
            project_id=request.nct_id,
            config={},
            hil_enabled=False,
        )
        params = models.SearchLitParams(
            disease_code="",
            keywords=[request.nct_id],
            sources=["clinicaltrials"],
            max_records=1,
            require_full_text=False,
        )

        corpus = fetcher.run(params, ctx)
        if not corpus.documents:
            raise HTTPException(status_code=404, detail=f"No data found for {request.nct_id}")

        doc = corpus.documents[0]
        nct_data = doc.metadata or {}

        # Step 2: Parse study metadata for example selection
        condition = nct_data.get("condition", ["unknown"])[0] if nct_data.get("condition") else "unknown"
        phase = nct_data.get("phase")
        study_metadata = {"condition": condition, "phase": phase, "keywords": []}

        # Step 3: Select examples using CorrectionManager
        manager = get_correction_manager()
        examples = manager.select_examples(study_metadata, num=5)

        # Step 4: Extract eligibility criteria
        extractor = get_extractor()
        extraction_result = extractor.extract(nct_data, examples)

        # Step 5: Prepare response
        # extraction_result already includes confidence_score
        confidence_score = extraction_result.get("confidence_score", 0.0)

        return ExtractResponse(
            nct_id=request.nct_id,
            extraction=extraction_result,  # Contains: inclusion, exclusion, confidence_score
            confidence_score=confidence_score,  # Explicitly pass confidence_score
            examples_used=[ex.get("nct_id", "unknown") for ex in examples],
            selection_strategy="cold_start" if len(examples) == 0 else "hybrid",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/review", response_model=ReviewResponse)
async def review_extraction(request: ReviewRequest):
    """
    Submit a review or correction of an extraction.

    This endpoint handles two actions:
    - 'accept': User accepts AI extraction as-is (no correction saved)
    - 'edit': User made corrections (save to corrections database)

    Args:
        request: ReviewRequest with action, original extraction, and optionally corrected version

    Returns:
        ReviewResponse with status and optional correction ID

    Raises:
        HTTPException: If validation fails or save fails
    """
    try:
        manager = get_correction_manager()

        if request.action == "accept":
            # User accepted as-is - no correction needed
            return ReviewResponse(
                status="accepted",
                message=f"Extraction for {request.nct_id} accepted without changes",
                correction_id=None,
            )

        elif request.action == "edit":
            # User made corrections - save to database
            if request.corrected_extraction is None:
                raise HTTPException(
                    status_code=400, detail="corrected_extraction required when action='edit'"
                )

            # Calculate changes (simplified - just count criteria differences)
            original_count = len(request.original_extraction.inclusion) + len(
                request.original_extraction.exclusion
            )
            corrected_count = len(request.corrected_extraction.inclusion) + len(
                request.corrected_extraction.exclusion
            )
            num_changes = abs(corrected_count - original_count)

            changes = [
                {
                    "field": "criteria_count",
                    "old": original_count,
                    "new": corrected_count,
                }
            ]

            correction_data = {
                "nct_id": request.nct_id,
                "corrected_by": "user@example.com",
                "timestamp": datetime.now().isoformat(),
                "extraction": {
                    "original_ai_output": request.original_extraction.model_dump(mode='json'),
                    "human_corrected": request.corrected_extraction.model_dump(mode='json'),
                    "changes": changes,
                },
                "metadata": {
                    "condition": "unknown",  # TODO: Extract from NCT data
                    "phase": None,
                    "keywords": request.keywords,
                },
            }

            result = manager.save_correction(correction_data)

            # Build correction file path
            correction_file = manager.data_dir / f"{request.nct_id}.json"

            return ReviewResponse(
                status="saved",
                message=f"Correction for {request.nct_id} saved successfully",
                correction_id=str(correction_file),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review submission failed: {str(e)}")


@router.get("/corrections/stats", response_model=CorrectionStatsResponse)
async def get_correction_stats():
    """
    Get statistics about the correction system.

    Returns aggregate metrics:
    - Total number of corrections
    - Corrections by condition
    - Corrections by keyword
    - Average quality score
    - Recent corrections

    Returns:
        CorrectionStatsResponse with system statistics
    """
    try:
        manager = get_correction_manager()
        index = manager.index

        # Count total corrections and calculate average quality score
        total_score = 0.0
        total_count = 0

        for nct_id, trial_data in index["trials"].items():
            # Each trial has a correction_count
            total_count += trial_data.get("correction_count", 0)

            # Load the actual correction file to get quality scores
            trial_file = manager.data_dir / f"{nct_id}.json"
            if trial_file.exists():
                with open(trial_file, "r") as f:
                    trial_file_data = json.load(f)
                    for version_data in trial_file_data.get("versions", {}).values():
                        total_score += version_data.get("quality_score", 0.0)

        avg_quality = total_score / total_count if total_count > 0 else 0.0

        # Convert index lists to counts
        by_condition_counts = {
            cond: len(nct_ids) for cond, nct_ids in index.get("by_condition", {}).items()
        }
        by_keyword_counts = {
            keyword: len(nct_ids) for keyword, nct_ids in index.get("by_keyword", {}).items()
        }

        return CorrectionStatsResponse(
            total_corrections=total_count,
            by_condition=by_condition_counts,
            by_keyword=by_keyword_counts,
            average_quality_score=avg_quality,
            recent_corrections=index.get("recent", []),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/corrections/{nct_id}")
async def get_correction_history(nct_id: str):
    """
    Get correction history for a specific NCT ID.

    Args:
        nct_id: NCT trial identifier (e.g., NCT03389555)

    Returns:
        Dict with correction history including all versions

    Raises:
        HTTPException: If NCT ID not found or invalid format
    """
    try:
        # Validate NCT ID format
        import re

        if not re.match(r"^NCT\d{8}$", nct_id):
            raise HTTPException(status_code=400, detail=f"Invalid NCT ID format: {nct_id}")

        manager = get_correction_manager()
        index = manager.index

        if nct_id not in index["trials"]:
            raise HTTPException(status_code=404, detail=f"No corrections found for {nct_id}")

        # Load actual correction file for full history
        trial_file = manager.data_dir / f"{nct_id}.json"
        if not trial_file.exists():
            raise HTTPException(status_code=404, detail=f"Correction file not found for {nct_id}")

        with open(trial_file, "r") as f:
            trial_file_data = json.load(f)

        trial_data = index["trials"][nct_id]
        return {
            "nct_id": nct_id,
            "latest_version": trial_data["latest_version"],
            "total_versions": len(trial_file_data.get("versions", {})),
            "correction_count": trial_data.get("correction_count", 0),
            "condition": trial_data.get("condition"),
            "keywords": trial_data.get("keywords", []),
            "versions": trial_file_data.get("versions", {}),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get correction history: {str(e)}")
