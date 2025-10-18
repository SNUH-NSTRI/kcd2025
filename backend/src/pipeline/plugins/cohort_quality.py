"""
Cohort Quality Assessment

Provides baseline covariate balance check (Treatment vs Control) and cohort characterization.
This is a pre-analysis sanity check for confounding bias and cohort quality.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu, chi2_contingency
from typing import Dict, List, Any, Optional


def convert_to_python_type(obj):
    """
    Convert numpy types to Python native types for JSON serialization.

    Args:
        obj: Any object that may contain numpy types

    Returns:
        Object with all numpy types converted to native Python types
    """
    # Check for numpy integer types
    if isinstance(obj, (np.integer,)):
        return int(obj)
    # Check for numpy floating types (NumPy 2.0 compatible)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    # Check for numpy boolean
    elif isinstance(obj, np.bool_):
        return bool(obj)
    # Check for numpy array
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    # Recursively handle dictionaries
    elif isinstance(obj, dict):
        return {key: convert_to_python_type(value) for key, value in obj.items()}
    # Recursively handle lists and tuples
    elif isinstance(obj, (list, tuple)):
        return [convert_to_python_type(item) for item in obj]
    return obj


class CohortQualityAssessor:
    """
    Assesses cohort quality through baseline balance and characterization.

    Part 1: Baseline Covariate Balance - Compares Treatment vs Control groups
    Part 2: Cohort Characterization - Descriptive statistics for the entire cohort
    """

    def __init__(
        self,
        cohort_data: pd.DataFrame,
        treatment_col: str = "treatment_group",
        treatment_value: int = 1,
        control_value: int = 0,
    ):
        """
        Initialize CohortQualityAssessor.

        Args:
            cohort_data: DataFrame containing cohort with baseline features
            treatment_col: Name of the treatment group column
            treatment_value: Value indicating treatment group (default: 1)
            control_value: Value indicating control group (default: 0)
        """
        self.cohort_data = cohort_data
        self.treatment_col = treatment_col

        # Partition into treatment and control groups
        self.treatment_df = cohort_data[
            cohort_data[treatment_col] == treatment_value
        ].copy()
        self.control_df = cohort_data[
            cohort_data[treatment_col] == control_value
        ].copy()

        self.balance_results: List[Dict[str, Any]] = []
        self.characterization: Dict[str, Any] = {}

    def _calculate_smd(self, variable: str) -> float:
        """
        Calculate Standardized Mean Difference for a continuous variable.

        SMD = (mean_treatment - mean_control) / pooled_std
        |SMD| > 0.1 indicates meaningful imbalance

        Args:
            variable: Name of the continuous variable

        Returns:
            Standardized Mean Difference
        """
        treatment_data = self.treatment_df[variable].dropna()
        control_data = self.control_df[variable].dropna()

        if len(treatment_data) == 0 or len(control_data) == 0:
            return 0.0

        mean_treatment = treatment_data.mean()
        mean_control = control_data.mean()

        std_treatment = treatment_data.std()
        std_control = control_data.std()

        # Pooled standard deviation
        n1, n2 = len(treatment_data), len(control_data)
        pooled_std = np.sqrt(
            ((n1 - 1) * std_treatment**2 + (n2 - 1) * std_control**2) / (n1 + n2 - 2)
        )

        if pooled_std == 0:
            return 0.0

        smd = (mean_treatment - mean_control) / pooled_std
        return float(smd)

    def _analyze_continuous_balance(self, variable: str) -> None:
        """
        Analyze baseline balance for a continuous variable.

        Uses SMD and Mann-Whitney U test.

        Args:
            variable: Name of the continuous variable
        """
        treatment_data = self.treatment_df[variable].dropna()
        control_data = self.control_df[variable].dropna()

        if len(treatment_data) == 0 or len(control_data) == 0:
            return

        smd = self._calculate_smd(variable)

        # Mann-Whitney U test (non-parametric)
        try:
            stat, p_val = mannwhitneyu(
                treatment_data, control_data, alternative="two-sided"
            )
        except Exception:
            p_val = np.nan

        # Overall cohort statistics
        overall_data = self.cohort_data[variable].dropna()

        self.balance_results.append(
            {
                "variable": variable,
                "type": "continuous",
                "smd": round(smd, 4),
                "p_value": round(p_val, 6) if not np.isnan(p_val) else None,
                "treatment_mean": round(treatment_data.mean(), 2),
                "treatment_std": round(treatment_data.std(), 2),
                "control_mean": round(control_data.mean(), 2),
                "control_std": round(control_data.std(), 2),
                "overall_mean": round(overall_data.mean(), 2),
                "overall_std": round(overall_data.std(), 2),
                "imbalanced": bool(abs(smd) > 0.1),
                "missing_pct": round(
                    (len(self.cohort_data) - len(overall_data))
                    / len(self.cohort_data)
                    * 100,
                    1,
                ),
            }
        )

    def _analyze_categorical_balance(self, variable: str) -> None:
        """
        Analyze baseline balance for a categorical variable.

        Uses Chi-square test of independence.

        Args:
            variable: Name of the categorical variable
        """
        treatment_col = self.treatment_df[variable].dropna()
        control_col = self.control_df[variable].dropna()

        if len(treatment_col) == 0 or len(control_col) == 0:
            return

        # Create contingency table
        all_data = pd.concat(
            [
                pd.DataFrame({"group": "treatment", variable: treatment_col}),
                pd.DataFrame({"group": "control", variable: control_col}),
            ]
        )

        contingency_table = pd.crosstab(all_data["group"], all_data[variable])

        if contingency_table.shape[0] < 2 or contingency_table.shape[1] < 2:
            return

        try:
            chi2, p_val, _, _ = chi2_contingency(contingency_table)
        except Exception:
            chi2, p_val = np.nan, np.nan

        # Calculate proportions
        treatment_counts = treatment_col.value_counts()
        control_counts = control_col.value_counts()
        overall_counts = self.cohort_data[variable].value_counts()

        treatment_dist = (
            (treatment_counts / len(treatment_col) * 100).round(1).to_dict()
        )
        control_dist = (control_counts / len(control_col) * 100).round(1).to_dict()
        overall_dist = (
            (overall_counts / len(self.cohort_data[variable].dropna()) * 100)
            .round(1)
            .to_dict()
        )

        self.balance_results.append(
            {
                "variable": variable,
                "type": "categorical",
                "chi2": round(chi2, 4) if not np.isnan(chi2) else None,
                "p_value": round(p_val, 6) if not np.isnan(p_val) else None,
                "treatment_dist": treatment_dist,
                "control_dist": control_dist,
                "overall_dist": overall_dist,
                "imbalanced": bool(p_val < 0.05) if not np.isnan(p_val) else False,
                "missing_pct": round(
                    self.cohort_data[variable].isna().sum()
                    / len(self.cohort_data)
                    * 100,
                    1,
                ),
            }
        )

    def assess_baseline_balance(
        self, continuous_vars: List[str], categorical_vars: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Assess baseline covariate balance between Treatment and Control groups.

        Args:
            continuous_vars: List of continuous variable names
            categorical_vars: List of categorical variable names

        Returns:
            List of balance assessment results
        """
        self.balance_results = []

        # Analyze continuous variables
        for var in continuous_vars:
            if var in self.cohort_data.columns:
                self._analyze_continuous_balance(var)

        # Analyze categorical variables
        for var in categorical_vars:
            if var in self.cohort_data.columns:
                self._analyze_categorical_balance(var)

        return self.balance_results

    def characterize_cohort(
        self, continuous_vars: List[str], categorical_vars: List[str]
    ) -> Dict[str, Any]:
        """
        Generate cohort characterization (descriptive statistics).

        Args:
            continuous_vars: List of continuous variable names
            categorical_vars: List of categorical variable names

        Returns:
            Dictionary with cohort characteristics
        """
        characteristics = {
            "sample_size": {
                "total": len(self.cohort_data),
                "treatment": len(self.treatment_df),
                "control": len(self.control_df),
            },
            "continuous": {},
            "categorical": {},
        }

        # Continuous variables
        for var in continuous_vars:
            if var in self.cohort_data.columns:
                data = self.cohort_data[var].dropna()
                if len(data) > 0:
                    characteristics["continuous"][var] = {
                        "mean": round(data.mean(), 2),
                        "std": round(data.std(), 2),
                        "median": round(data.median(), 2),
                        "q25": round(data.quantile(0.25), 2),
                        "q75": round(data.quantile(0.75), 2),
                        "min": round(data.min(), 2),
                        "max": round(data.max(), 2),
                        "missing_pct": round(
                            (len(self.cohort_data) - len(data))
                            / len(self.cohort_data)
                            * 100,
                            1,
                        ),
                    }

        # Categorical variables
        for var in categorical_vars:
            if var in self.cohort_data.columns:
                counts = self.cohort_data[var].value_counts()
                total = self.cohort_data[var].dropna().shape[0]
                characteristics["categorical"][var] = {
                    "counts": counts.to_dict(),
                    "percentages": (counts / total * 100).round(1).to_dict(),
                    "missing_pct": round(
                        self.cohort_data[var].isna().sum()
                        / len(self.cohort_data)
                        * 100,
                        1,
                    ),
                }

        self.characterization = characteristics
        return characteristics

    def run_full_assessment(
        self, continuous_vars: List[str], categorical_vars: List[str]
    ) -> Dict[str, Any]:
        """
        Run full cohort quality assessment.

        Combines baseline balance check and cohort characterization.

        Args:
            continuous_vars: List of continuous variable names
            categorical_vars: List of categorical variable names

        Returns:
            Complete assessment results (all numpy types converted to Python native types)
        """
        balance_results = self.assess_baseline_balance(continuous_vars, categorical_vars)
        characterization = self.characterize_cohort(continuous_vars, categorical_vars)

        imbalanced_count = sum(1 for r in balance_results if r.get("imbalanced", False))

        results = {
            "summary": {
                "total_patients": len(self.cohort_data),
                "treatment_count": len(self.treatment_df),
                "control_count": len(self.control_df),
                "variables_analyzed": len(balance_results),
                "imbalanced_variables": imbalanced_count,
            },
            "baseline_balance": balance_results,
            "cohort_characteristics": characterization,
        }

        # Convert all numpy types to Python native types for JSON serialization
        return convert_to_python_type(results)


# Default variable lists for MIMIC-IV baseline data
DEFAULT_CONTINUOUS_VARS = [
    "age_at_admission",
    "anchor_age",
    "height_cm",
    "weight_kg",
    "bmi",
    "temperature",
    "heart_rate",
    "sbp",
    "dbp",
    "respiratory_rate",
    "spo2",
    "lactate",
    "creatinine",
    "wbc",
    "platelets",
    "sodium",
    "potassium",
    "glucose",
    "apache_ii_score",
    "charlson_score",
]

DEFAULT_CATEGORICAL_VARS = [
    "gender",
    "race",
    "first_careunit",
    "chf",
    "mi",
    "pvd",
    "cvd",
    "copd",
    "diabetes",
    "ckd",
    "liver_disease",
    "cancer",
]
