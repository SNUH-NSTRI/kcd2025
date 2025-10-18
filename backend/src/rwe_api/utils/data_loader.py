"""Data loading utilities with automatic feature type conversion.

This module provides centralized data loading functions that automatically
apply correct data types to baseline characteristics CSV files.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Union

import pandas as pd


def load_cohort_with_types(csv_path: Union[str, Path]) -> pd.DataFrame:
    """
    Load cohort CSV with automatic baseline feature type conversion.

    This function attempts to use feature_types_utils.py for automatic type
    conversion. If not available, falls back to standard pd.read_csv().

    Args:
        csv_path: Path to the cohort CSV file (typically *_with_baseline.csv)

    Returns:
        DataFrame with correctly typed columns:
            - Continuous features → float64
            - Binary features → Int8
            - Categorical features → category
            - Ordinal features → Int16

    Example:
        >>> from rwe_api.utils.data_loader import load_cohort_with_types
        >>> df = load_cohort_with_types('cohorts/NCT123_med_v3.1_with_baseline.csv')
        >>> df['anchor_age'].dtype  # float64 (continuous)
        >>> df['chf'].dtype  # Int8 (binary)
        >>> df['gender'].dtype  # category (categorical)
    """
    csv_path = Path(csv_path)

    # Add scripts directory to path for feature_types_utils import
    scripts_path = Path(__file__).parents[3] / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))

    try:
        from feature_types_utils import load_baseline_characteristics

        df = load_baseline_characteristics(str(csv_path))
        return df

    except ImportError:
        # Fallback: standard CSV loading without type conversion
        return pd.read_csv(csv_path)


def load_cohort_sample(csv_path: Union[str, Path], n_rows: int = 10) -> pd.DataFrame:
    """
    Load first N rows of cohort CSV with automatic type conversion.

    Note: This loads the full file first to ensure correct type conversion,
    then returns the first N rows. For very large files (>1M rows), consider
    using nrows parameter in pd.read_csv() for better performance.

    Args:
        csv_path: Path to the cohort CSV file
        n_rows: Number of rows to return (default: 10)

    Returns:
        DataFrame with first N rows and correctly typed columns

    Example:
        >>> df_sample = load_cohort_sample('cohorts/file.csv', n_rows=100)
        >>> len(df_sample)
        100
    """
    df = load_cohort_with_types(csv_path)
    return df.head(n_rows)
