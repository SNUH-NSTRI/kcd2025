"""
Medicine search API endpoints.
"""

from fastapi import APIRouter, Query
from typing import List
from ..medicines import Medicine, search_medicines

router = APIRouter(prefix="/api/medicines", tags=["medicines"])


@router.get("/search", response_model=List[Medicine])
async def search_medicines_endpoint(
    q: str = Query(None, description="Search query string", min_length=1),
    limit: int = Query(20, description="Maximum number of results", ge=1, le=100)
) -> List[Medicine]:
    """
    Search for medicines based on a query string.

    Performs case-insensitive substring matching on medicine display names
    (format: "parent - variant").

    Args:
        q: Search query string (required)
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        List of matching Medicine objects
    """
    if not q:
        return []

    return search_medicines(query=q, limit=limit)
