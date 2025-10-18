"""
Causal Forest Estimator Module.

This module provides a wrapper class for EconML's CausalForestDML model,
aligning with the platform's estimator pattern. It encapsulates the logic for
fitting the model, estimating effects (ATE, CATE, feature importances), and
calculating SHAP values for CATE.
"""
from __future__ import annotations

from typing import Any
import logging

import pandas as pd
import numpy as np
from econml.dml import CausalForestDML
from sklearn.ensemble import GradientBoostingRegressor

logger = logging.getLogger(__name__)


class CausalForestEstimator:
    """
    A wrapper for EconML's CausalForestDML to estimate Conditional Average Treatment Effects (CATE).

    This estimator is designed to fit into a reusable pattern, providing methods to
    fit the model, estimate causal effects, and compute SHAP values for interpreting
    treatment effect heterogeneity.
    """

    def __init__(
        self,
        treatment: str,
        outcome: str,
        covariates: list[str],
        effect_modifiers: list[str],
        n_estimators: int = 100,
        min_samples_leaf: int = 10,
        max_depth: int | None = None,
        random_state: int = 42,
    ):
        """
        Initialize the CausalForestEstimator.

        Args:
            treatment: The name of the treatment column.
            outcome: The name of the outcome column.
            covariates: A list of names for confounding variables (W).
            effect_modifiers: A list of names for variables that modify the treatment effect (X).
            n_estimators: Number of trees in the forest.
            min_samples_leaf: Minimum samples per leaf.
            max_depth: Maximum tree depth.
            random_state: The random state for reproducibility.
        """
        self.treatment = treatment
        self.outcome = outcome
        self.covariates = covariates
        self.effect_modifiers = effect_modifiers
        self.n_estimators = n_estimators
        self.min_samples_leaf = min_samples_leaf
        self.max_depth = max_depth
        self.random_state = random_state

        self.model = CausalForestDML(
            model_y=GradientBoostingRegressor(random_state=self.random_state),
            model_t=GradientBoostingRegressor(random_state=self.random_state),
            n_estimators=self.n_estimators,
            min_samples_leaf=self.min_samples_leaf,
            max_depth=self.max_depth,
            random_state=self.random_state,
        )
        self.results: dict[str, Any] = {}
        self.shap_results: dict[str, Any] = {}
        self._X: pd.DataFrame | None = None
        self._fitted = False

    def fit(self, data: pd.DataFrame) -> CausalForestEstimator:
        """
        Fit the Causal Forest model to the provided data.

        Args:
            data: The input DataFrame containing all necessary columns.

        Returns:
            The fitted estimator instance.
        """
        logger.info(f"Fitting Causal Forest with {len(data)} samples")

        # Handle NaN values - drop rows with any NaN in required columns
        required_cols = [self.outcome, self.treatment] + self.effect_modifiers
        if self.covariates:
            required_cols += self.covariates

        # Create mask for complete cases
        mask = data[required_cols].notna().all(axis=1)
        n_dropped = (~mask).sum()

        if n_dropped > 0:
            logger.warning(f"Dropping {n_dropped} samples with missing values ({n_dropped/len(data)*100:.1f}%)")

        # Filter data
        Y = data[self.outcome][mask]
        T = data[self.treatment][mask]
        X = data[self.effect_modifiers][mask]
        W = data[self.covariates][mask] if self.covariates else None

        if len(Y) < 100:
            raise ValueError(f"Insufficient complete cases for Causal Forest: {len(Y)} samples (minimum 100 required)")

        logger.info(f"Fitting with {len(Y)} complete samples (dropped {n_dropped} with NaN)")

        # Store complete X and mask for later predictions
        self._X = X
        self._mask = mask

        self.model.fit(Y, T, X=X, W=W)
        self._fitted = True

        logger.info("Causal Forest fitted successfully")
        return self

    def estimate_effect(self) -> dict[str, Any]:
        """
        Estimate the ATE, CATEs, and feature importances for heterogeneity.

        This method should be called after `fit()`.

        Returns:
            A dictionary containing the ATE, a list of CATE estimates,
            and a dictionary of feature importances.
        """
        if not self._fitted or self._X is None:
            raise RuntimeError("The model must be fitted before estimating effects.")

        ate = self.model.ate(self._X)
        cate_estimates = self.model.effect(self._X)
        feature_importances = dict(
            zip(self.effect_modifiers, self.model.feature_importances_)
        )

        self.results = {
            "ate": float(ate),
            "cate_estimates": cate_estimates.flatten().tolist(),
            "feature_importances": feature_importances,
            "effect_modifiers_names": list(self.effect_modifiers),
        }

        logger.info(
            f"Effects estimated. ATE: {ate:.4f}, "
            f"CATE range: [{cate_estimates.min():.4f}, {cate_estimates.max():.4f}]"
        )

        return self.results

    def calculate_shap_values(
        self, sample_size: int | None = None
    ) -> dict[str, Any]:
        """
        Calculate SHAP values for the CATE model to explain effect heterogeneity.

        This is a computationally intensive operation.

        Args:
            sample_size: The number of samples to use for SHAP calculation.
                         If None, uses the full dataset.

        Returns:
            A dictionary containing SHAP values, base value (ATE), feature names,
            and the corresponding feature values for visualization.
        """
        if not self._fitted or self._X is None:
            raise RuntimeError("The model must be fitted before calculating SHAP values.")

        X_to_explain = self._X
        if sample_size and sample_size < len(self._X):
            X_to_explain = self._X.sample(n=sample_size, random_state=self.random_state)
            logger.info(f"Using {sample_size} samples for SHAP calculation")
        else:
            logger.info(f"Using all {len(self._X)} samples for SHAP calculation")

        # This call correctly computes SHAP values for the CATE model.
        # NOTE: econml's shap_values() returns a dictionary structure
        # We need to extract the actual SHAP values array
        try:
            import shap
            shap_values_raw = self.model.shap_values(X_to_explain)

            # econml wraps SHAP Explanation object, extract the values
            if hasattr(shap_values_raw, 'values') and not callable(shap_values_raw.values):
                cate_shap_values = shap_values_raw.values
            elif isinstance(shap_values_raw, np.ndarray):
                cate_shap_values = shap_values_raw
            elif isinstance(shap_values_raw, dict):
                # econml sometimes returns nested dict, try to find the array
                logger.debug(f"SHAP returned dict with keys: {shap_values_raw.keys()}")
                # Try common patterns
                if len(shap_values_raw) > 0:
                    first_val = next(iter(shap_values_raw.values()))
                    if hasattr(first_val, 'values'):
                        cate_shap_values = first_val.values
                    elif isinstance(first_val, np.ndarray):
                        cate_shap_values = first_val
                    else:
                        raise ValueError(f"Cannot extract SHAP values from dict structure: {type(first_val)}")
                else:
                    raise ValueError("SHAP returned empty dict")
            else:
                raise ValueError(f"Unexpected SHAP return type: {type(shap_values_raw)}")

            # Convert to list for JSON serialization
            shap_values_list = cate_shap_values.tolist()

        except Exception as e:
            logger.error(f"Failed to compute SHAP values: {e}")
            # Return empty results if SHAP computation fails
            self.shap_results = {
                "shap_values": [],
                "base_value": self.results.get("ate"),
                "feature_names": list(self.effect_modifiers),
                "feature_values": [],
                "error": str(e),
            }
            return self.shap_results

        self.shap_results = {
            "shap_values": shap_values_list,
            "base_value": self.results.get("ate"),
            "feature_names": list(self.effect_modifiers),
            "feature_values": X_to_explain.values.tolist(),
        }

        logger.info(f"SHAP values calculated for {len(X_to_explain)} samples")

        return self.shap_results

    @property
    def feature_importances_(self) -> np.ndarray:
        """
        Get feature importances from the fitted model.

        Returns:
            Array of feature importances.
        """
        if not self._fitted:
            raise RuntimeError("The model must be fitted before accessing feature importances.")
        return self.model.feature_importances_
