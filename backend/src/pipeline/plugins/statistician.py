"""
Statistician Plugin: Advanced Statistical Analysis for RWE Clinical Trials

This plugin implements professional statistical methods for causal inference:
1. IPTW (Inverse Probability of Treatment Weighting) for covariate balancing
2. Cox Proportional Hazards for survival analysis
3. Causal Forest for heterogeneous treatment effects (HTE)
4. Shapley values for feature importance and criteria optimization
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Mapping

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from lifelines import CoxPHFitter
import shap

try:
    from econml.dml import CausalForestDML
    from .estimators.causal_forest import CausalForestEstimator
    ECONML_AVAILABLE = True
except ImportError:
    ECONML_AVAILABLE = False
    CausalForestEstimator = None  # type: ignore
    logging.warning("econml not available - Causal Forest will be disabled")

from ..context import PipelineContext
from .. import models


logger = logging.getLogger(__name__)


class Statistician:
    """
    Advanced statistical analyzer implementing professional causal inference methods.

    This analyzer replaces synthetic data generation with real statistical estimation:
    - Propensity score weighting (IPTW) for confounding adjustment
    - Cox PH for time-to-event outcomes with censoring
    - Causal Forest for personalized treatment effects
    - Shapley attribution for eligibility criteria optimization
    """

    def __init__(self, config: models.StatisticianConfig | None = None):
        """
        Initialize Statistician with configuration.

        Args:
            config: Configuration for statistical methods. If None, uses defaults.
        """
        self.config = config or models.StatisticianConfig()
        self._causal_forest_estimator: CausalForestEstimator | None = None
        logger.info(f"Statistician initialized with config: {self.config}")

    def run(
        self,
        params: models.AnalyzeParams,
        ctx: PipelineContext,
        cohort: models.CohortResult,
    ) -> models.AnalysisMetrics:
        """
        Execute statistical analysis pipeline.

        Args:
            params: Analysis parameters including treatment/outcome columns
            ctx: Pipeline context
            cohort: Cohort data with patient rows

        Returns:
            AnalysisMetrics with detailed statistical results
        """
        if not params.estimators:
            raise ValueError("at least one estimator must be provided")

        cohort_rows = list(cohort.rows)
        if not cohort_rows:
            raise ValueError("cohort must contain at least one row")

        logger.info(f"Starting statistical analysis for {len(cohort_rows)} subjects")

        # Convert cohort to DataFrame for analysis
        df = self._cohort_to_dataframe(cohort_rows, params)

        # Validate required columns
        self._validate_data(df, params)

        # Run statistical methods
        outcomes: list[models.OutcomeRecord] = []

        # 1. IPTW: Propensity scores and weights
        if self.config.use_iptw:
            logger.info("Computing propensity scores (IPTW)...")
            df = self._compute_iptw(df, params)

        # 2. Cox PH: Survival analysis (if time-to-event data available)
        if self.config.use_cox_ph and self.config.time_column in df.columns:
            logger.info("Running Cox Proportional Hazards analysis...")
            df = self._compute_cox_ph(df, params)

        # 3. Causal Forest: HTE analysis
        if self.config.use_causal_forest and ECONML_AVAILABLE:
            logger.info("Computing heterogeneous treatment effects (Causal Forest)...")
            df = self._compute_causal_forest(df, params)

        # 4. Shapley: Feature importance
        if self.config.use_shapley:
            logger.info("Computing Shapley values for feature attribution...")
            df = self._compute_shapley(df, params)

        # Convert results back to OutcomeRecord objects
        outcomes = self._dataframe_to_outcomes(df, cohort_rows)

        # Compute aggregate metrics
        metrics = self._compute_metrics(df, params, outcomes)

        logger.info(f"Analysis complete. Generated {len(outcomes)} outcome records.")

        return models.AnalysisMetrics(
            schema_version="analysis.v2",
            outcomes=outcomes,
            metrics=metrics,
        )

    def _cohort_to_dataframe(
        self, cohort_rows: list[models.CohortRow], params: models.AnalyzeParams
    ) -> pd.DataFrame:
        """Convert cohort rows to pandas DataFrame for analysis."""
        data = []
        for row in cohort_rows:
            record = {
                "subject_id": row.subject_id,
                "stay_id": row.stay_id,
                "index_time": row.index_time,
                "matched_criteria": ",".join(row.matched_criteria),
            }

            # Add features
            if row.features:
                record.update(row.features)

            data.append(record)

        df = pd.DataFrame(data)
        logger.info(f"Converted cohort to DataFrame: {df.shape[0]} rows, {df.shape[1]} columns")
        return df

    def _validate_data(self, df: pd.DataFrame, params: models.AnalyzeParams) -> None:
        """Validate that required columns exist in the data."""
        required = [params.treatment_column, params.outcome_column]
        missing = [col for col in required if col not in df.columns]

        if missing:
            raise ValueError(
                f"Missing required columns: {missing}. "
                f"Available columns: {list(df.columns)}"
            )

        logger.info(f"Data validation passed. Treatment: {params.treatment_column}, Outcome: {params.outcome_column}")

    def _compute_iptw(
        self, df: pd.DataFrame, params: models.AnalyzeParams
    ) -> pd.DataFrame:
        """
        Compute Inverse Probability of Treatment Weights (IPTW).

        IPTW reweights the sample to create pseudo-populations where treatment
        assignment is independent of measured confounders.
        """
        # Get covariate columns (exclude outcome and treatment)
        covariates = self.config.covariates
        if covariates is None:
            # Auto-detect: numeric columns excluding treatment and outcome
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            covariates = [
                col for col in numeric_cols
                if col not in [params.treatment_column, params.outcome_column, "subject_id"]
            ]

        if not covariates:
            logger.warning("No covariates found for propensity score estimation. Using empty model.")
            df["propensity"] = 0.5
            df["iptw_weight"] = 1.0
            return df

        # Prepare data
        X = df[covariates].fillna(0)  # Handle missing values
        treatment = df[params.treatment_column].astype(int)

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Fit logistic regression for propensity scores
        lr = LogisticRegression(random_state=self.config.random_state, max_iter=1000)
        lr.fit(X_scaled, treatment)

        # Predict propensity scores
        propensity_scores = lr.predict_proba(X_scaled)[:, 1]
        df["propensity"] = propensity_scores

        # Compute IPTW weights
        weights = np.where(
            treatment == 1,
            1 / propensity_scores,
            1 / (1 - propensity_scores)
        )

        # Clip weights to prevent extreme values
        if self.config.iptw_clip:
            lower, upper = self.config.iptw_clip
            weights = np.clip(weights,
                            np.quantile(weights, lower),
                            np.quantile(weights, upper))

        # Stabilize weights (optional)
        if self.config.iptw_stabilize:
            weights = weights / weights.mean()

        df["iptw_weight"] = weights

        logger.info(
            f"IPTW computed. Mean propensity: {propensity_scores.mean():.3f}, "
            f"Weight range: [{weights.min():.3f}, {weights.max():.3f}]"
        )

        return df

    def _compute_cox_ph(
        self, df: pd.DataFrame, params: models.AnalyzeParams
    ) -> pd.DataFrame:
        """
        Compute Cox Proportional Hazards model for survival analysis.

        Cox PH models time-to-event outcomes while handling censoring,
        estimating hazard ratios for treatment effects.
        """
        time_col = self.config.time_column
        event_col = self.config.event_column

        if time_col not in df.columns or event_col not in df.columns:
            logger.warning(
                f"Cox PH requires {time_col} and {event_col} columns. Skipping."
            )
            df["hazard_ratio"] = None
            df["survival_prob"] = None
            return df

        # Prepare data for Cox model
        covariates = [params.treatment_column]
        if self.config.covariates:
            covariates.extend(
                [c for c in self.config.covariates if c in df.columns]
            )

        cox_data = df[[time_col, event_col] + covariates].copy()
        cox_data = cox_data.dropna()

        if len(cox_data) < 10:
            logger.warning("Insufficient data for Cox PH model. Skipping.")
            df["hazard_ratio"] = None
            df["survival_prob"] = None
            return df

        # Fit Cox PH model
        cph = CoxPHFitter(alpha=self.config.cox_alpha)
        cph.fit(cox_data, duration_col=time_col, event_col=event_col)

        # Extract hazard ratio for treatment
        treatment_hr = cph.hazard_ratios_[params.treatment_column]
        df["hazard_ratio"] = treatment_hr

        # Compute survival probabilities at median time
        median_time = df[time_col].median()
        survival_probs = cph.predict_survival_function(
            df[covariates].fillna(0),
            times=[median_time]
        ).iloc[0].values

        df["survival_prob"] = survival_probs

        logger.info(
            f"Cox PH fitted. Treatment HR: {treatment_hr:.3f}, "
            f"p-value: {cph.summary.loc[params.treatment_column, 'p']:.4f}"
        )

        return df

    def _compute_causal_forest(
        self, df: pd.DataFrame, params: models.AnalyzeParams
    ) -> pd.DataFrame:
        """
        Compute Conditional Average Treatment Effects (CATE) using Causal Forest.

        Causal Forest discovers heterogeneous treatment effects across patient
        subgroups, enabling personalized treatment recommendations.

        Now uses the dedicated CausalForestEstimator class for better modularity.
        """
        if not ECONML_AVAILABLE:
            logger.warning("econml not installed. Skipping Causal Forest.")
            df["cate_value"] = None
            df["cate_group"] = None
            return df

        # Get covariates (effect modifiers)
        covariates = self.config.covariates
        if covariates is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            covariates = [
                col for col in numeric_cols
                if col not in [params.treatment_column, params.outcome_column, "subject_id"]
            ]

        if not covariates:
            logger.warning("No covariates for Causal Forest. Skipping.")
            df["cate_value"] = None
            df["cate_group"] = None
            return df

        # Initialize and fit the CausalForestEstimator
        estimator = CausalForestEstimator(
            treatment=params.treatment_column,
            outcome=params.outcome_column,
            covariates=[],  # W: confounders (none in this case)
            effect_modifiers=covariates,  # X: heterogeneity features
            n_estimators=self.config.cf_n_estimators,
            min_samples_leaf=self.config.cf_min_samples_leaf,
            max_depth=self.config.cf_max_depth,
            random_state=self.config.random_state,
        )

        estimator.fit(df)
        results = estimator.estimate_effect()

        # Add CATE values to dataframe
        df["cate_value"] = results["cate_estimates"]

        # Group by CATE magnitude
        cate_values = np.array(results["cate_estimates"])
        cate_quantiles = np.quantile(cate_values, [0.33, 0.67])
        df["cate_group"] = pd.cut(
            cate_values,
            bins=[-np.inf, cate_quantiles[0], cate_quantiles[1], np.inf],
            labels=["low_benefit", "moderate_benefit", "high_benefit"]
        ).astype(str)

        logger.info(
            f"Causal Forest fitted. ATE: {results['ate']:.3f}, "
            f"CATE range: [{cate_values.min():.3f}, {cate_values.max():.3f}]"
        )

        # Store estimator for potential SHAP calculation later
        self._causal_forest_estimator = estimator

        return df

    def _compute_shapley(
        self, df: pd.DataFrame, params: models.AnalyzeParams
    ) -> pd.DataFrame:
        """
        Compute Shapley values for feature importance.

        Shapley values quantify each feature's contribution to the outcome,
        enabling identification of which eligibility criteria are most impactful.
        """
        covariates = self.config.covariates
        if covariates is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            covariates = [
                col for col in numeric_cols
                if col not in [params.treatment_column, params.outcome_column, "subject_id"]
            ]

        if not covariates:
            logger.warning("No covariates for Shapley computation. Skipping.")
            df["shapley_values"] = [{}] * len(df)
            return df

        # Prepare data
        X = df[covariates].fillna(0)
        Y = df[params.outcome_column].fillna(0)

        # Train a simple model for SHAP explanation
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(
            n_estimators=50,
            random_state=self.config.random_state,
            max_depth=5
        )
        model.fit(X, Y)

        # Compute SHAP values (use TreeExplainer for efficiency)
        explainer = shap.TreeExplainer(model)

        # Sample data if too large
        n_samples = min(len(X), self.config.shapley_max_samples)
        X_sample = X.sample(n=n_samples, random_state=self.config.random_state)

        shap_values = explainer.shap_values(X_sample)

        # Convert to per-subject dictionaries
        shapley_dicts = []
        for i in range(len(df)):
            if i < n_samples:
                shapley_dict = {
                    cov: float(shap_values[i, j])
                    for j, cov in enumerate(covariates)
                }
            else:
                shapley_dict = {}
            shapley_dicts.append(shapley_dict)

        df["shapley_values"] = shapley_dicts

        logger.info(f"Shapley values computed for {n_samples} subjects.")

        return df

    def _dataframe_to_outcomes(
        self, df: pd.DataFrame, cohort_rows: list[models.CohortRow]
    ) -> list[models.OutcomeRecord]:
        """Convert analysis DataFrame back to OutcomeRecord objects."""
        outcomes = []

        for i, row in df.iterrows():
            cohort_row = cohort_rows[i]

            outcomes.append(
                models.OutcomeRecord(
                    subject_id=row["subject_id"],
                    propensity=float(row.get("propensity", 0.0)) if pd.notna(row.get("propensity")) else None,
                    ate=None,  # Will be computed in metrics
                    cate_group=row.get("cate_group", None),
                    predicted_outcome=None,
                    iptw_weight=float(row.get("iptw_weight", 1.0)) if pd.notna(row.get("iptw_weight")) else None,
                    hazard_ratio=float(row.get("hazard_ratio")) if pd.notna(row.get("hazard_ratio")) else None,
                    survival_prob=float(row.get("survival_prob")) if pd.notna(row.get("survival_prob")) else None,
                    cate_value=float(row.get("cate_value")) if pd.notna(row.get("cate_value")) else None,
                    shapley_values=row.get("shapley_values", {}),
                    metadata={
                        "matched_criteria": list(cohort_row.matched_criteria),
                        "feature_snapshot": dict(cohort_row.features or {}),
                    },
                )
            )

        return outcomes

    def _compute_metrics(
        self, df: pd.DataFrame, params: models.AnalyzeParams, outcomes: list[models.OutcomeRecord]
    ) -> Mapping[str, Any]:
        """Compute aggregate metrics from analysis results."""
        metrics = {
            "schema_version": "analysis.v2",
            "estimators": list(params.estimators),
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "summary": {
                "n_subjects": len(outcomes),
            },
        }

        # IPTW metrics
        if "iptw_weight" in df.columns:
            weights = df["iptw_weight"].dropna()
            metrics["summary"]["iptw"] = {
                "mean_weight": float(weights.mean()),
                "weight_range": [float(weights.min()), float(weights.max())],
                "effective_sample_size": float((weights.sum() ** 2) / (weights ** 2).sum()),
            }

        # Cox PH metrics
        if "hazard_ratio" in df.columns:
            hr_values = df["hazard_ratio"].dropna()
            if len(hr_values) > 0:
                metrics["summary"]["cox_ph"] = {
                    "hazard_ratio": float(hr_values.iloc[0]) if len(hr_values) > 0 else None,
                    "mean_survival_prob": float(df["survival_prob"].dropna().mean()) if "survival_prob" in df.columns else None,
                }

        # Causal Forest metrics
        if "cate_value" in df.columns:
            cate_values = df["cate_value"].dropna()
            if len(cate_values) > 0:
                metrics["summary"]["causal_forest"] = {
                    "mean_cate": float(cate_values.mean()),
                    "cate_std": float(cate_values.std()),
                    "cate_range": [float(cate_values.min()), float(cate_values.max())],
                    "positive_response_rate": float((cate_values > 0).mean()),
                }

        # Shapley metrics (top features)
        if "shapley_values" in df.columns:
            all_shapley = [s for s in df["shapley_values"] if s]
            if all_shapley:
                feature_importance = {}
                for shapley_dict in all_shapley:
                    for feat, val in shapley_dict.items():
                        if feat not in feature_importance:
                            feature_importance[feat] = []
                        feature_importance[feat].append(abs(val))

                # Average absolute SHAP values
                avg_importance = {
                    feat: np.mean(vals)
                    for feat, vals in feature_importance.items()
                }

                # Top 10 features
                top_features = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:10]

                metrics["summary"]["shapley"] = {
                    "top_features": [
                        {"feature": feat, "importance": float(imp)}
                        for feat, imp in top_features
                    ]
                }

        return metrics

    def compute_cate_shap_values(self, sample_size: int | None = None) -> dict[str, Any]:
        """
        Compute SHAP values for the Causal Forest CATE estimates.

        This method should be called after running the analysis pipeline with
        Causal Forest enabled. It provides interpretation of treatment effect
        heterogeneity.

        Args:
            sample_size: Number of samples to use for SHAP calculation.
                        If None, uses all samples (may be slow).

        Returns:
            Dictionary containing SHAP values, base value (ATE), feature names,
            and feature values for visualization.

        Raises:
            RuntimeError: If Causal Forest has not been run yet.
        """
        if self._causal_forest_estimator is None:
            raise RuntimeError(
                "Causal Forest has not been fitted. "
                "Please run the analysis pipeline with use_causal_forest=True first."
            )

        logger.info(
            f"Computing SHAP values for CATE "
            f"(sample_size={'all' if sample_size is None else sample_size})"
        )

        shap_results = self._causal_forest_estimator.calculate_shap_values(
            sample_size=sample_size
        )

        return shap_results
