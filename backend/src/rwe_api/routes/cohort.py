"""Cohort quality assessment endpoints."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from rwe_api.config import settings  # Centralized config
from rwe_api.utils import load_cohort_with_types, load_cohort_sample
from pipeline.plugins.cohort_quality import (
    CohortQualityAssessor,
    DEFAULT_CONTINUOUS_VARS,
    DEFAULT_CATEGORICAL_VARS,
)

router = APIRouter()

# Use centralized config (ALWAYS loads .env)
PROJECT_ROOT = settings.PROJECT_ROOT


class CohortQualityRequest(BaseModel):
    """Request model for cohort quality assessment."""

    nct_id: str
    medication: str


class SamplePatientsRequest(BaseModel):
    """Request model for sample patients."""

    nct_id: str
    medication: str
    limit: int = 10  # Default to first 10 patients


class CohortSummaryRequest(BaseModel):
    """Request model for cohort summary statistics."""

    nct_id: str
    medication: str


@router.post("/assess-quality")
async def assess_cohort_quality(request: CohortQualityRequest):
    """
    Assess cohort quality through baseline balance and characterization.

    Part 1: Baseline Covariate Balance - Compare Treatment vs Control groups
    Part 2: Cohort Characterization - Descriptive statistics for entire cohort

    Args:
        request: CohortQualityRequest with nct_id and medication

    Returns:
        Cohort quality assessment results with:
        - summary: total patients, treatment/control counts, imbalanced variables
        - baseline_balance: SMD, p-values, and group statistics
        - cohort_characteristics: descriptive statistics (Table 1 format)
    """
    try:
        # Construct file path
        cohort_dir = PROJECT_ROOT / request.nct_id / "cohorts" / request.medication

        # Find baseline CSV (with_baseline)
        baseline_files = list(
            cohort_dir.glob(f"{request.nct_id}_{request.medication}_v*_with_baseline.csv")
        )

        if not baseline_files:
            raise HTTPException(
                status_code=404,
                detail=f"Baseline data not found for {request.nct_id}/{request.medication}",
            )

        baseline_file = sorted(baseline_files)[-1]  # Use most recent version

        # ✅ Load cohort data with automatic feature type conversion
        cohort_data = load_cohort_with_types(baseline_file)

        # Verify treatment_group column exists
        if "treatment_group" not in cohort_data.columns:
            raise HTTPException(
                status_code=400,
                detail="treatment_group column not found in cohort data",
            )

        # Initialize CohortQualityAssessor
        assessor = CohortQualityAssessor(
            cohort_data=cohort_data,
            treatment_col="treatment_group",
            treatment_value=1,
            control_value=0,
        )

        # Run full assessment with default variables
        results = assessor.run_full_assessment(
            continuous_vars=DEFAULT_CONTINUOUS_VARS,
            categorical_vars=DEFAULT_CATEGORICAL_VARS,
        )

        return {
            "status": "success",
            "nct_id": request.nct_id,
            "medication": request.medication,
            "data": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sample-patients")
async def get_sample_patients(request: SamplePatientsRequest):
    """
    Fetch a limited sample of patients from the cohort for preview.

    Args:
        request: SamplePatientsRequest with nct_id, medication, and limit

    Returns:
        Sample patient records (limited to first N rows)
    """
    try:
        # Construct file path
        cohort_dir = PROJECT_ROOT / request.nct_id / "cohorts" / request.medication

        # Find baseline CSV (with_baseline)
        baseline_files = list(
            cohort_dir.glob(f"{request.nct_id}_{request.medication}_v*_with_baseline.csv")
        )

        if not baseline_files:
            raise HTTPException(
                status_code=404,
                detail=f"Cohort data not found for {request.nct_id}/{request.medication}",
            )

        baseline_file = sorted(baseline_files)[-1]  # Use most recent version

        # ✅ Load sample data with automatic feature type conversion
        cohort_data = load_cohort_sample(baseline_file, n_rows=request.limit)

        # Convert to records format for JSON serialization
        # Select key columns for display
        display_columns = [
            "subject_id",
            "age_at_admission",
            "gender",
            "treatment_group",
            "icu_intime",
            "icu_outtime",
            "los",  # Length of stay
            "any_vasopressor",
            "mortality",
        ]

        # Filter to only existing columns
        available_columns = [col for col in display_columns if col in cohort_data.columns]
        sample_data = cohort_data[available_columns]

        # Convert to list of dicts
        patients = sample_data.to_dict(orient="records")

        return {
            "status": "success",
            "nct_id": request.nct_id,
            "medication": request.medication,
            "limit": request.limit,
            "count": len(patients),
            "patients": patients,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summary")
async def get_cohort_summary(request: CohortSummaryRequest):
    """
    Calculate cohort summary statistics in real-time.

    Computes:
    - Attrition funnel (from metadata.json if available, else simple 2-step)
    - Characteristics (age, gender distributions)
    - All calculated on-the-fly from CSV (~50ms for 11k patients)

    Args:
        request: CohortSummaryRequest with nct_id and medication

    Returns:
        Real-time computed summary statistics
    """
    try:
        # Construct file path
        cohort_dir = PROJECT_ROOT / request.nct_id / "cohorts" / request.medication

        # Find baseline CSV
        baseline_files = list(
            cohort_dir.glob(f"{request.nct_id}_{request.medication}_v*_with_baseline.csv")
        )

        if not baseline_files:
            raise HTTPException(
                status_code=404,
                detail=f"Cohort data not found for {request.nct_id}/{request.medication}",
            )

        baseline_file = sorted(baseline_files)[-1]

        # ✅ Load cohort data with automatic feature type conversion
        df = load_cohort_with_types(baseline_file)

        # Calculate basic counts
        total_patients = len(df)
        treatment_count = int((df['treatment_group'] == 1).sum())
        control_count = int((df['treatment_group'] == 0).sum())

        # Try to load attrition funnel from metadata.json
        metadata_file = cohort_dir / "metadata.json"
        attrition_funnel = None

        if metadata_file.exists():
            import json
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    attrition_funnel = metadata.get('attrition_funnel')
            except Exception:
                pass  # If metadata read fails, fall back to simple funnel

        # Fallback: Simple 2-step funnel if metadata not available
        if not attrition_funnel:
            attrition_funnel = [
                {
                    'step': 0,
                    'criteriaId': 'INITIAL',
                    'description': 'All patients in MIMIC-IV',
                    'patients_remaining': 41142,
                },
                {
                    'step': 1,
                    'criteriaId': 'FINAL',
                    'description': 'Final cohort after all criteria',
                    'patients_remaining': total_patients,
                },
            ]

        # Calculate characteristics
        age_stats = {
            'mean': round(float(df['age_at_admission'].mean()), 1),
            'std': round(float(df['age_at_admission'].std()), 1),
            'median': round(float(df['age_at_admission'].median()), 1),
            'min': int(df['age_at_admission'].min()),
            'max': int(df['age_at_admission'].max()),
        }

        gender_counts = df['gender'].value_counts().to_dict()
        gender_dist = {
            'M': int(gender_counts.get('M', 0)),
            'F': int(gender_counts.get('F', 0)),
        }

        # Mortality stats (as percentage, 1 decimal)
        mortality_rate = round(float((df['mortality'] == 1).mean()) * 100, 1)

        # Vasopressor usage (as percentage, 1 decimal)
        vasopressor_rate = round(float((df['any_vasopressor'] == 1).mean()) * 100, 1)

        return {
            'status': 'success',
            'nct_id': request.nct_id,
            'medication': request.medication,
            'data': {
                'attrition': {
                    'total': total_patients,
                    'treatment': treatment_count,
                    'control': control_count,
                    'funnel': attrition_funnel,
                    'initial_count': attrition_funnel[0]['patients_remaining'] if attrition_funnel else 41142,
                },
                'characteristics': {
                    'age': age_stats,
                    'gender': gender_dist,
                    'mortality_rate': mortality_rate,
                    'vasopressor_rate': vasopressor_rate,
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
