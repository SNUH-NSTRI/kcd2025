"""
Cache management API endpoints.

Provides endpoints to view, validate, and manage the shared criterion cache.
"""

from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.trialist_hybrid.shared_cache import SharedCriterionCache
from rwe_api.config import settings

router = APIRouter()

# Initialize cache
CACHE_DIR = Path(__file__).parent.parent.parent.parent / "cache"
cache = SharedCriterionCache(CACHE_DIR)


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    version: str
    mimic_version: str
    total_entries: int
    hit_count: int
    miss_count: int
    hit_rate: float
    popular_criteria: List[Dict[str, Any]]


class ValidateCacheRequest(BaseModel):
    """Request to validate a cached criterion."""
    criterion_text: str
    validated_by: str
    notes: str = None


class SearchCacheRequest(BaseModel):
    """Request to search cache."""
    query: str
    limit: int = 10


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get cache statistics.

    Returns:
        Cache metadata with hit/miss rates and popular criteria
    """
    try:
        stats = cache.get_stats()
        return CacheStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {e}")


@router.get("/search")
async def search_cache(query: str, limit: int = 10):
    """
    Search cache for similar criteria.

    Args:
        query: Search query string
        limit: Maximum results to return (default: 10)

    Returns:
        List of matching cache entries
    """
    try:
        results = cache.search(query, limit=limit)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.post("/validate")
async def validate_criterion(request: ValidateCacheRequest):
    """
    Mark a cached criterion as validated.

    This indicates the mapping has been manually verified against MIMIC-IV.

    Args:
        request: Validation request with criterion text and validator info

    Returns:
        Success confirmation
    """
    try:
        success = cache.validate(
            criterion_text=request.criterion_text,
            validated_by=request.validated_by
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Criterion not found in cache: {request.criterion_text}"
            )

        return {
            "success": True,
            "message": f"Criterion validated by {request.validated_by}",
            "criterion": request.criterion_text
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@router.delete("/criterion")
async def delete_criterion(criterion_text: str):
    """
    Remove a criterion from cache.

    Args:
        criterion_text: Criterion text to delete

    Returns:
        Success confirmation
    """
    try:
        success = cache.delete(criterion_text)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Criterion not found: {criterion_text}"
            )

        return {
            "success": True,
            "message": "Criterion deleted from cache",
            "criterion": criterion_text
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {e}")


@router.post("/clear")
async def clear_cache(confirm: str):
    """
    Clear entire cache.

    DANGER: This removes all cached mappings.

    Args:
        confirm: Must be "YES_DELETE_ALL_CACHE" to proceed

    Returns:
        Success confirmation
    """
    if confirm != "YES_DELETE_ALL_CACHE":
        raise HTTPException(
            status_code=400,
            detail="Confirmation string incorrect. Cache NOT cleared."
        )

    try:
        cache.clear()
        return {
            "success": True,
            "message": "Cache cleared successfully",
            "warning": "All cached mappings have been removed"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear failed: {e}")


@router.get("/export-validated")
async def export_validated():
    """
    Export only validated mappings.

    Returns:
        Count of validated entries exported
    """
    try:
        output_path = CACHE_DIR / "validated_mappings_export.json"
        count = cache.export_validated_only(output_path)

        return {
            "success": True,
            "validated_count": count,
            "export_path": str(output_path),
            "message": f"Exported {count} validated mappings"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@router.get("/entry/{criterion_text}")
async def get_cache_entry(criterion_text: str):
    """
    Get detailed cache entry for specific criterion.

    Args:
        criterion_text: Criterion text to look up

    Returns:
        Full cache entry with mapping details
    """
    try:
        mapping = cache.get(criterion_text)

        if mapping is None:
            raise HTTPException(
                status_code=404,
                detail=f"Criterion not found in cache: {criterion_text}"
            )

        return {
            "criterion_text": criterion_text,
            "mapping": mapping,
            "cached": True
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup failed: {e}")
