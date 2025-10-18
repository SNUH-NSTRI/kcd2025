"""
Test utilities for SQL string comparisons.
"""
from __future__ import annotations


def normalize_sql(sql: str | None) -> str:
    """
    Removes extra whitespace and standardizes formatting for comparison.

    This allows for flexible formatting in expected SQL strings within tests
    while ensuring a robust, whitespace-agnostic comparison.
    """
    if not sql:
        return ""
    # Collapse all whitespace to single spaces and trim
    return " ".join(sql.strip().split())
