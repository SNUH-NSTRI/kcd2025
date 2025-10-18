"""
Cohort extraction utilities for MIMIC-IV clinical trial analysis.

This module provides tools for:
1. Building eligible patient caches (first admission + 24h medication)
2. Extracting NCT-specific cohorts with treatment assignment
3. Calculating survival outcomes
"""

from pathlib import Path

__version__ = "1.0.0"
__all__ = ["utils"]
