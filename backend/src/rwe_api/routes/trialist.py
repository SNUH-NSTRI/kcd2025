"""Trialist mapper API endpoints."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pipeline.intelligent_mapper import IntelligentMimicMapper, MappingResult

logger = logging.getLogger(__name__)

router = APIRouter()


class MapConceptRequest(BaseModel):
    """Request schema for concept mapping."""
    concept: str
    domain: str


class MapConceptResponse(BaseModel):
    """Response schema for concept mapping."""
    mapping: dict
    confidence: float
    reasoning: str
    alternatives: list
    source: str
    timestamp: str


@router.post("/map-concept", response_model=MapConceptResponse)
async def map_concept(request: MapConceptRequest):
    """Map a clinical concept to MIMIC-IV database tables.

    Args:
        request: Contains concept text and clinical domain

    Returns:
        MapConceptResponse with mapping details

    Example:
        POST /api/trialist/map-concept
        {
            "concept": "Patients with sepsis",
            "domain": "Condition"
        }
    """
    try:
        # Initialize mapper
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENROUTER_API_KEY not configured"
            )

        # Path to mapping cache
        cache_path = Path("backend/src/pipeline/mimic_concept_mapping_v2.json")

        mapper = IntelligentMimicMapper(
            mapping_file=cache_path,
            openrouter_api_key=api_key,
            model="openai/gpt-4o-mini"
        )

        # Perform mapping
        result: MappingResult = mapper.map_concept(
            concept=request.concept,
            domain=request.domain
        )

        # Convert to response format
        return MapConceptResponse(
            mapping={
                "table": result.mapping.table,
                "columns": result.mapping.columns,
                "filter_logic": result.mapping.filter_logic,
            },
            confidence=result.confidence,
            reasoning=result.reasoning,
            alternatives=[
                {
                    "table": alt.table,
                    "columns": alt.columns,
                    "filter_logic": alt.filter_logic,
                    "reasoning": alt.reasoning,
                }
                for alt in result.alternatives
            ],
            source=result.source,
            timestamp=result.timestamp,
        )

    except Exception as e:
        logger.error(f"Error mapping concept: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
