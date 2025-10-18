"""
Multi-Method Matching Module

Implements multiple matching methods for causal inference:
1. PSM (Propensity Score Matching)
2. PSM with Caliper (0.01 default)
3. Mahalanobis Distance Matching
4. IPTW (Inverse Probability of Treatment Weighting)

Compares methods using SMD (Standardized Mean Difference) and provides
LLM-based method selection with reasoning.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import warnings
import logging

from .baseline_comparison import calculate_smd

# Import feature type utilities
try:
    import sys
    from pathlib import Path as P
    # __file__ is .../backend/src/agents/statistician/analysis/multi_method_matching.py
    # Need to go up to project root, then into scripts/
    project_root = P(__file__).parents[5]  # Go up to datathon_20251017/
    scripts_path = project_root / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    from feature_types_utils import get_feature_type, FEATURE_METADATA
    HAS_FEATURE_TYPES = True
except ImportError as e:
    HAS_FEATURE_TYPES = False
    FEATURE_METADATA = {}
    import logging
    logging.getLogger(__name__).debug(f"feature_types_utils import failed: {e}")

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class MultiMethodMatcher:
    """
    Applies multiple matching methods and compares their balance quality.
    
    Attributes:
        df: DataFrame with treatment_group and baseline characteristics
        covariates: List of covariate column names for matching
    """

    def __init__(self, df: pd.DataFrame, covariates: List[str]):
        """
        Initialize multi-method matcher.

        Args:
            df: DataFrame with 'treatment_group' column and covariates
            covariates: List of covariate names to use for matching

        Raises:
            ValueError: If treatment_group column is missing or not binary
        """
        if 'treatment_group' not in df.columns:
            raise ValueError("Input DataFrame must contain a 'treatment_group' column.")
        if df['treatment_group'].nunique() != 2:
            raise ValueError(
                f"'treatment_group' column must be binary (contain exactly 2 unique values), "
                f"found {df['treatment_group'].nunique()} unique values."
            )

        self.df = df.copy()
        self.covariates = covariates
        
        # Use feature_types_utils if available
        if HAS_FEATURE_TYPES:
            logger.info("  Using feature_types_utils for proper type classification")
            self.cont_vars = [c for c in covariates if c in FEATURE_METADATA and FEATURE_METADATA[c]['type'] == 'continuous']
            self.cat_vars = [c for c in covariates if c in FEATURE_METADATA and FEATURE_METADATA[c]['type'] in ['binary', 'categorical']]
            self.ordinal_vars = [c for c in covariates if c in FEATURE_METADATA and FEATURE_METADATA[c]['type'] == 'ordinal']
            logger.info(f"    Continuous: {len(self.cont_vars)}, Binary/Categorical: {len(self.cat_vars)}, Ordinal: {len(self.ordinal_vars)}")
        else:
            logger.warning("  feature_types_utils not available, using heuristic classification")
            # Fallback: hardcoded lists
            self._cont_vars_list = [
                # Demographics & Anthropometrics
                "age_at_admission", "anchor_age", "height_cm", "weight_kg", "bmi",
                # Vital Signs
                "temperature", "heart_rate", "sbp", "dbp", "respiratory_rate", "spo2",
                # Laboratory Values
                "ph", "po2", "pco2", "hematocrit", "hemoglobin", "wbc", "platelets",
                "sodium", "potassium", "chloride", "glucose", "ast", "alt", "alp", "ggt",
                "d_dimer", "fibrinogen", "pt", "aptt", "bun", "creatinine", "lactate",
                "total_protein", "albumin", "crp", "procalcitonin",
                # Outcomes (usually should NOT be covariates, but classify correctly)
                "outcome_days", "los"
            ]

            self._cat_vars_list = [
                # Demographics
                "gender", "race",
                # Comorbidities
                "chf", "mi", "pvd", "cvd", "copd", "diabetes", "ckd", "liver_disease", "cancer",
                # Organ Support
                "mechanical_ventilation", "renal_replacement_therapy",
                "ventilation", "vasopressor",  # Legacy names
                # Vasopressors (specific agents)
                "vasopressor_norepinephrine", "vasopressor_phenylephrine",
                "vasopressor_vasopressin", "vasopressor_epinephrine", "any_vasopressor"
            ]

            self._ordinal_vars_list = ["gcs", "apache_ii", "apache_ii_score", "charlson_score", "sofa_score"]
            
            self.cont_vars = [c for c in covariates if c in self._cont_vars_list]
            self.cat_vars = [c for c in covariates if c in self._cat_vars_list]
            self.ordinal_vars = [c for c in covariates if c in self._ordinal_vars_list]
    
    def _calculate_propensity_scores(self) -> np.ndarray:
        """
        Calculate propensity scores using a logistic regression model with
        type-specific preprocessing for covariates.

        Applies appropriate preprocessing for each feature type:
        - Continuous: mean imputation + standardization (StandardScaler)
        - Ordinal: median imputation + standardization
        - Binary: mode imputation (preserves {0, 1})
        - Nominal: mode imputation + one-hot encoding

        This ensures continuous/ordinal features don't dominate binary features
        due to scale differences in the propensity score model.

        Note: Propensity scores are recalculated on each call to ensure
        freshness if df or covariates change. No caching is used.
        """
        if not self.covariates:
            logger.warning("No covariates specified for propensity score calculation. Returning base rate.")
            base_rate = self.df['treatment_group'].mean()
            return np.full(len(self.df), base_rate)

        X = self.df[self.covariates]
        y = self.df['treatment_group'].values.astype(int)

        # Robustly separate categorical variables into binary and nominal (for one-hot encoding)
        binary_vars = [c for c in self.cat_vars if self.df[c].nunique(dropna=False) <= 2]
        nominal_vars = [c for c in self.cat_vars if self.df[c].nunique(dropna=False) > 2]

        # Warn about high-cardinality nominal variables
        for var in nominal_vars:
            cardinality = self.df[var].nunique()
            if cardinality > 20:  # Threshold can be adjusted
                logger.warning(
                    f"Nominal variable '{var}' has high cardinality ({cardinality} unique values). "
                    f"This may create a large number of features and could affect model performance."
                )

        logger.info(
            f"    Propensity model features: {len(self.cont_vars)} continuous, "
            f"{len(self.ordinal_vars)} ordinal, {len(binary_vars)} binary, {len(nominal_vars)} nominal."
        )

        # Define preprocessing pipelines for each feature type
        continuous_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='mean')),
            ('scaler', StandardScaler())
        ])

        ordinal_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])

        # For binary variables, we only need to impute missing values.
        binary_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent'))
        ])

        # For nominal (multi-level categorical) variables, impute then one-hot encode.
        nominal_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', drop='if_binary'))
        ])

        # Dynamically build the list of transformers for ColumnTransformer.
        # This gracefully handles cases where some feature types are absent.
        transformers = []
        if self.cont_vars:
            transformers.append(('continuous', continuous_transformer, self.cont_vars))
        if self.ordinal_vars:
            transformers.append(('ordinal', ordinal_transformer, self.ordinal_vars))
        if binary_vars:
            transformers.append(('binary', binary_transformer, binary_vars))
        if nominal_vars:
            transformers.append(('nominal', nominal_transformer, nominal_vars))

        # CRITICAL: Verify all covariates are accounted for
        processed_cols = set()
        for name, trans, cols in transformers:
            processed_cols.update(cols)

        unprocessed_cols = set(self.covariates) - processed_cols
        if unprocessed_cols:
            raise ValueError(
                f"CRITICAL: The following covariates were not classified and would not be scaled: "
                f"{list(unprocessed_cols)}. This would reintroduce the scale-dominance bug. "
                f"Please add these features to FEATURE_METADATA or the fallback classification lists."
            )

        if not transformers:
            logger.warning("No features available for propensity model after classification. Returning base rate.")
            base_rate = self.df['treatment_group'].mean()
            return np.full(len(self.df), base_rate)

        # Create the preprocessor
        preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder='drop'  # Drop unclassified covariates (validation above ensures none exist)
        )

        # Create the full model pipeline
        model_pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', LogisticRegression(max_iter=1000, solver='lbfgs', random_state=42))
        ])

        # Fit the pipeline and predict propensity scores
        model_pipeline.fit(X, y)
        propensity_scores = model_pipeline.predict_proba(X)[:, 1]

        return propensity_scores
    
    def match_psm(self, caliper: Optional[float] = None) -> pd.DataFrame:
        """
        Perform PSM matching (1:1 nearest neighbor).
        Match each treatment subject to nearest control subject.
        
        Args:
            caliper: Optional caliper in propensity score units (e.g., 0.01)
        
        Returns:
            Matched DataFrame with both treatment and control subjects
        """
        ps = self._calculate_propensity_scores()
        
        treatment_mask = self.df['treatment_group'] == 1
        control_mask = self.df['treatment_group'] == 0
        
        n_treatment = treatment_mask.sum()
        n_control = control_mask.sum()
        
        logger.info(f"  PSM matching: {n_treatment} treatment, {n_control} control subjects")
        
        treatment_indices = self.df[treatment_mask].index.tolist()
        control_indices = self.df[control_mask].index.tolist()
        
        treatment_ps = ps[treatment_mask]
        control_ps = ps[control_mask]
        
        # Match each treatment to nearest control (not the reverse!)
        distances = np.abs(treatment_ps[:, np.newaxis] - control_ps[np.newaxis, :])
        min_indices = distances.argmin(axis=1)  # For each treatment, find nearest control
        min_distances = distances.min(axis=1)
        
        # Apply caliper if specified
        matched_pairs = []
        used_controls = set()
        
        for i, (treat_idx, min_dist, match_idx) in enumerate(
            zip(treatment_indices, min_distances, min_indices)
        ):
            if caliper is None or min_dist <= caliper:
                ctrl_idx = control_indices[match_idx]
                # Avoid reusing same control (1:1 matching)
                if ctrl_idx not in used_controls:
                    matched_pairs.append((treat_idx, ctrl_idx))
                    used_controls.add(ctrl_idx)
        
        logger.info(f"  PSM matched {len(matched_pairs)} pairs (caliper={caliper})")
        
        if len(matched_pairs) == 0:
            logger.warning(f"  No matches found with caliper={caliper}")
            return pd.DataFrame()
        
        # Create matched dataset
        matched_treatment_indices = [pair[0] for pair in matched_pairs]
        matched_control_indices = [pair[1] for pair in matched_pairs]
        
        matched_df = pd.concat([
            self.df.loc[matched_treatment_indices],
            self.df.loc[matched_control_indices]
        ]).reset_index(drop=True)
        
        logger.info(f"  PSM matched_df: {len(matched_df)} total subjects ({len(matched_pairs)} pairs)")
        
        return matched_df
    
    def match_mahalanobis(self) -> pd.DataFrame:
        """
        Perform Mahalanobis distance matching.
        
        Uses continuous variables only for distance calculation.
        
        Returns:
            Matched DataFrame with both treatment and control subjects
        """
        treatment_mask = self.df['treatment_group'] == 1
        control_mask = self.df['treatment_group'] == 0
        
        # Use continuous variables for Mahalanobis
        use_cols = [col for col in self.cont_vars if col in self.df.columns]
        if not use_cols:
            use_cols = self.covariates
        
        treatment_data = self.df[treatment_mask][use_cols].copy()
        control_data = self.df[control_mask][use_cols].copy()
        
        # Handle missing values
        for col in treatment_data.columns:
            overall_mean = pd.concat([treatment_data[col], control_data[col]]).mean()
            treatment_data[col] = treatment_data[col].fillna(overall_mean)
            control_data[col] = control_data[col].fillna(overall_mean)
        
        # Standardize
        scaler = StandardScaler()
        treatment_scaled = scaler.fit_transform(treatment_data.values)
        control_scaled = scaler.transform(control_data.values)
        
        # Compute covariance matrix
        cov_matrix = np.cov(treatment_scaled.T)
        
        # Calculate Mahalanobis distances with regularization
        try:
            # Add small regularization term to diagonal to handle singular matrices
            reg_term = 1e-6 * np.eye(cov_matrix.shape[0])
            inv_cov = np.linalg.inv(cov_matrix + reg_term)
            distances = pairwise_distances(
                control_scaled, treatment_scaled,
                metric='mahalanobis', VI=inv_cov
            )
            logger.info("Mahalanobis distance calculated successfully")
        except np.linalg.LinAlgError as e:
            # If still fails, use pseudo-inverse as robust alternative
            logger.warning(f"Mahalanobis inversion failed ({e}), trying pseudo-inverse")
            try:
                inv_cov = np.linalg.pinv(cov_matrix)
                distances = pairwise_distances(
                    control_scaled, treatment_scaled,
                    metric='mahalanobis', VI=inv_cov
                )
                logger.info("Mahalanobis distance calculated with pseudo-inverse")
            except Exception as e2:
                logger.error(f"Both inversion methods failed ({e2}), falling back to Euclidean")
                distances = pairwise_distances(control_scaled, treatment_scaled, metric='euclidean')
        
        # Find nearest neighbors (match each treatment to nearest control)
        treatment_indices = self.df[treatment_mask].index.tolist()
        control_indices = self.df[control_mask].index.tolist()
        
        n_treatment = len(treatment_indices)
        n_control = len(control_indices)
        
        logger.info(f"  Mahalanobis matching: {n_treatment} treatment, {n_control} control subjects")
        
        # Match each treatment to nearest control
        min_indices = distances.argmin(axis=1)  # For each treatment, find nearest control
        
        matched_pairs = []
        used_controls = set()
        
        for i, (treat_idx, match_idx) in enumerate(zip(treatment_indices, min_indices)):
            ctrl_idx = control_indices[match_idx]
            # Avoid reusing same control (1:1 matching)
            if ctrl_idx not in used_controls:
                matched_pairs.append((treat_idx, ctrl_idx))
                used_controls.add(ctrl_idx)
        
        logger.info(f"  Mahalanobis matched {len(matched_pairs)} pairs")
        
        # Create matched dataset
        matched_treatment_indices = [pair[0] for pair in matched_pairs]
        matched_control_indices = [pair[1] for pair in matched_pairs]
        
        matched_df = pd.concat([
            self.df.loc[matched_treatment_indices],
            self.df.loc[matched_control_indices]
        ]).reset_index(drop=True)
        
        logger.info(f"  Mahalanobis matched_df: {len(matched_df)} total subjects ({len(matched_pairs)} pairs)")
        
        return matched_df
    
    def apply_iptw(self) -> pd.DataFrame:
        """
        Calculate IPTW weights and return weighted dataset.
        
        Returns:
            DataFrame with 'iptw_weight' column added
        """
        ps = self._calculate_propensity_scores()
        treatment = self.df['treatment_group'].values.astype(int)
        p_t = treatment.mean()
        
        # Calculate stabilized weights
        numerator = np.where(treatment == 1, p_t, 1 - p_t)
        denominator = np.where(treatment == 1, ps, 1 - ps)
        
        # Avoid division by zero
        denominator = np.clip(denominator, 0.01, 0.99)
        weights = numerator / denominator
        
        # Add weights to dataframe
        df_weighted = self.df.copy()
        df_weighted['iptw_weight'] = weights
        
        return df_weighted
    
    def calculate_smd_for_method(
        self, 
        matched_df: pd.DataFrame, 
        iptw_weights: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Calculate SMD for all covariates after matching/weighting.
        
        Args:
            matched_df: Matched dataset
            iptw_weights: Optional IPTW weights (for IPTW method)
        
        Returns:
            Dictionary mapping covariate name to SMD value
        """
        if len(matched_df) == 0:
            logger.warning("Empty matched_df - cannot calculate SMD")
            return {}
        
        treatment_mask = matched_df['treatment_group'] == 1
        control_mask = matched_df['treatment_group'] == 0
        
        n_treatment = treatment_mask.sum()
        n_control = control_mask.sum()
        
        logger.info(f"  Calculating SMD for {len(self.covariates)} covariates")
        logger.info(f"    Matched dataset: {n_treatment} treatment, {n_control} control")
        
        smd_dict = {}
        failed_vars = []
        
        for var in self.covariates:
            if var not in matched_df.columns:
                continue
            
            try:
                treatment_data = matched_df.loc[treatment_mask, var]
                control_data = matched_df.loc[control_mask, var]
                
                # Skip if no valid data
                if treatment_data.isna().all() or control_data.isna().all():
                    logger.warning(f"    Variable '{var}' has all NaN values - skipping")
                    continue
                
                # Determine variable type using feature_types_utils
                if HAS_FEATURE_TYPES and var in FEATURE_METADATA:
                    feature_type = FEATURE_METADATA[var]['type']
                    is_binary = feature_type == 'binary'
                    is_ordinal = feature_type == 'ordinal'
                    # For ordinal (gcs, apache_ii, charlson_score), treat as continuous for SMD
                    if is_ordinal:
                        is_binary = False
                        logger.debug(f"    Variable '{var}' is ordinal - treating as continuous for SMD")
                else:
                    # Fallback to heuristic
                    is_binary = var in self.cat_vars or matched_df[var].nunique() <= 2
                    is_ordinal = var in getattr(self, 'ordinal_vars', [])
                    if is_ordinal:
                        is_binary = False
                
                # Calculate weighted SMD for IPTW
                if iptw_weights is not None:
                    treatment_indices = np.where(treatment_mask)[0]
                    control_indices = np.where(control_mask)[0]
                    
                    treatment_weights = iptw_weights[treatment_indices]
                    control_weights = iptw_weights[control_indices]
                    
                    # Drop NaN values and corresponding weights
                    t_valid = ~treatment_data.isna()
                    c_valid = ~control_data.isna()
                    
                    t_data_clean = treatment_data[t_valid].values
                    c_data_clean = control_data[c_valid].values
                    t_weights_clean = treatment_weights[t_valid]
                    c_weights_clean = control_weights[c_valid]
                    
                    if len(t_data_clean) == 0 or len(c_data_clean) == 0:
                        continue
                    
                    # Weighted mean
                    mean1 = np.average(t_data_clean, weights=t_weights_clean)
                    mean2 = np.average(c_data_clean, weights=c_weights_clean)
                    
                    # Weighted variance
                    if is_binary:
                        var1 = mean1 * (1 - mean1)
                        var2 = mean2 * (1 - mean2)
                    else:
                        var1 = np.average((t_data_clean - mean1)**2, weights=t_weights_clean)
                        var2 = np.average((c_data_clean - mean2)**2, weights=c_weights_clean)
                    
                    pooled_std = np.sqrt((var1 + var2) / 2)
                    smd = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0.0
                else:
                    # Standard SMD calculation
                    smd = calculate_smd(treatment_data, control_data, is_binary=is_binary)
                    
                    if np.isnan(smd):
                        logger.warning(f"    Variable '{var}' returned NaN SMD")
                        failed_vars.append(var)
                        continue
                
                smd_dict[var] = abs(smd)
                
            except Exception as e:
                logger.warning(f"    Failed to calculate SMD for '{var}': {e}")
                failed_vars.append(var)
                continue
        
        logger.info(f"  SMD calculated for {len(smd_dict)}/{len(self.covariates)} covariates")
        if failed_vars:
            logger.warning(f"  Failed variables: {failed_vars[:5]}...")
        
        return smd_dict
    
    def _extract_baseline_stats(self, matched_df: pd.DataFrame, method_name: str) -> Dict[str, Dict]:
        """
        Extract baseline characteristics for a matched dataset.
        
        Returns summary statistics for key variables (mean±SD for continuous, n(%) for categorical).
        """
        if len(matched_df) == 0:
            return {}
        
        treatment_mask = matched_df['treatment_group'] == 1
        control_mask = matched_df['treatment_group'] == 0
        
        treatment_data = matched_df[treatment_mask]
        control_data = matched_df[control_mask]
        
        baseline_stats = {}
        
        # Key continuous variables
        key_continuous = ['anchor_age', 'lactate', 'temperature', 'heart_rate', 'sbp', 
                         'wbc', 'creatinine', 'apache_ii']
        
        for var in key_continuous:
            if var in matched_df.columns:
                t_mean = treatment_data[var].mean()
                t_std = treatment_data[var].std()
                c_mean = control_data[var].mean()
                c_std = control_data[var].std()
                
                baseline_stats[var] = {
                    'treatment': f"{t_mean:.1f}±{t_std:.1f}" if not np.isnan(t_mean) else "N/A",
                    'control': f"{c_mean:.1f}±{c_std:.1f}" if not np.isnan(c_mean) else "N/A"
                }
        
        # Key categorical variables (comorbidities)
        key_categorical = ['chf', 'mi', 'copd', 'diabetes', 'ckd', 'ventilation', 'vasopressor']
        
        for var in key_categorical:
            if var in matched_df.columns:
                t_n = (treatment_data[var] == 1).sum()
                t_pct = (t_n / len(treatment_data) * 100) if len(treatment_data) > 0 else 0
                c_n = (control_data[var] == 1).sum()
                c_pct = (c_n / len(control_data) * 100) if len(control_data) > 0 else 0
                
                baseline_stats[var] = {
                    'treatment': f"{t_n} ({t_pct:.1f}%)",
                    'control': f"{c_n} ({c_pct:.1f}%)"
                }
        
        return baseline_stats
    
    def compare_all_methods(self) -> Dict[str, Dict]:
        """
        Run all matching methods and compare their balance quality.
        NOW includes baseline characteristics for each method!
        
        Returns:
            Dictionary with method names as keys and results as values:
            {
                'psm': {
                    'matched_df': df, 
                    'smd_dict': {...}, 
                    'mean_smd': 0.05, 
                    'balanced_pct': 0.95,
                    'baseline_stats': {...}  ← NEW!
                },
                ...
            }
        """
        results = {}
        
        # 1. PSM (no caliper)
        logger.info("Running PSM (no caliper)...")
        psm_matched = self.match_psm(caliper=None)
        logger.info(f"  PSM returned matched_df with {len(psm_matched)} subjects")
        
        psm_smd = self.calculate_smd_for_method(psm_matched)
        logger.info(f"  PSM SMD calculated: {len(psm_smd)} variables, mean={np.mean(list(psm_smd.values())) if psm_smd else 'N/A'}")
        
        psm_baseline = self._extract_baseline_stats(psm_matched, 'psm')
        
        mean_smd_val = np.mean(list(psm_smd.values())) if psm_smd and len(psm_smd) > 0 else np.nan
        balanced_pct_val = sum(v < 0.1 for v in psm_smd.values()) / len(psm_smd) if psm_smd and len(psm_smd) > 0 else 0.0
        
        results['psm'] = {
            'matched_df': psm_matched,
            'smd_dict': psm_smd,
            'mean_smd': mean_smd_val,
            'balanced_pct': balanced_pct_val,
            'n_matched': len(psm_matched) // 2 if len(psm_matched) > 0 else 0,
            'baseline_stats': psm_baseline
        }
        logger.info(f"  PSM results: mean_smd={mean_smd_val}, balanced_pct={balanced_pct_val:.1%}")
        
        # 2. PSM with Caliper (0.01)
        logger.info("Running PSM with caliper=0.01...")
        psm_caliper_matched = self.match_psm(caliper=0.01)
        psm_caliper_smd = self.calculate_smd_for_method(psm_caliper_matched)
        psm_caliper_baseline = self._extract_baseline_stats(psm_caliper_matched, 'psm_caliper')
        results['psm_caliper'] = {
            'matched_df': psm_caliper_matched,
            'smd_dict': psm_caliper_smd,
            'mean_smd': np.mean(list(psm_caliper_smd.values())) if psm_caliper_smd else np.nan,
            'balanced_pct': sum(v < 0.1 for v in psm_caliper_smd.values()) / len(psm_caliper_smd) if psm_caliper_smd else 0.0,
            'n_matched': len(psm_caliper_matched) // 2 if len(psm_caliper_matched) > 0 else 0,
            'baseline_stats': psm_caliper_baseline
        }
        
        # 3. Mahalanobis Distance
        logger.info("Running Mahalanobis matching...")
        mahal_matched = self.match_mahalanobis()
        mahal_smd = self.calculate_smd_for_method(mahal_matched)
        mahal_baseline = self._extract_baseline_stats(mahal_matched, 'mahalanobis')
        results['mahalanobis'] = {
            'matched_df': mahal_matched,
            'smd_dict': mahal_smd,
            'mean_smd': np.mean(list(mahal_smd.values())) if mahal_smd else np.nan,
            'balanced_pct': sum(v < 0.1 for v in mahal_smd.values()) / len(mahal_smd) if mahal_smd else 0.0,
            'n_matched': len(mahal_matched) // 2 if len(mahal_matched) > 0 else 0,
            'baseline_stats': mahal_baseline
        }
        
        # 4. IPTW
        logger.info("Running IPTW...")
        iptw_df = self.apply_iptw()
        iptw_smd = self.calculate_smd_for_method(iptw_df, iptw_weights=iptw_df['iptw_weight'].values)
        iptw_baseline = self._extract_baseline_stats(iptw_df, 'iptw')
        results['iptw'] = {
            'matched_df': iptw_df,
            'smd_dict': iptw_smd,
            'mean_smd': np.mean(list(iptw_smd.values())) if iptw_smd else np.nan,
            'balanced_pct': sum(v < 0.1 for v in iptw_smd.values()) / len(iptw_smd) if iptw_smd else 0.0,
            'n_matched': len(iptw_df),  # IPTW uses all subjects
            'baseline_stats': iptw_baseline
        }
        
        return results
    
    def generate_comparison_summary(self, results: Dict[str, Dict]) -> str:
        """
        Generate a text summary comparing all methods.
        
        Args:
            results: Output from compare_all_methods()
        
        Returns:
            Formatted text summary
        """
        lines = []
        lines.append("=" * 80)
        lines.append("MATCHING METHODS COMPARISON")
        lines.append("=" * 80)
        lines.append("")
        
        for method_name, result in results.items():
            lines.append(f"Method: {method_name.upper()}")
            lines.append(f"  N matched pairs: {result['n_matched']}")
            lines.append(f"  Mean SMD: {result['mean_smd']:.4f}")
            lines.append(f"  Balanced variables (SMD < 0.1): {result['balanced_pct']:.1%}")
            lines.append(f"  Total variables: {len(result['smd_dict'])}")
            lines.append("")
        
        return "\n".join(lines)


def select_best_method_with_llm(
    comparison_results: Dict[str, Dict],
    covariates: List[str],
    openrouter_api_key: Optional[str] = None
) -> Tuple[str, str]:
    """
    Use LLM to select the best matching method with detailed reasoning.
    
    Args:
        comparison_results: Output from compare_all_methods()
        covariates: List of covariate names
        openrouter_api_key: OpenRouter API key (uses env var if None)
    
    Returns:
        Tuple of (selected_method_name, reasoning_text)
    """
    import os
    import requests
    
    api_key = openrouter_api_key or os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        logger.warning("No OpenRouter API key provided, using default selection")
        return _select_best_method_default(comparison_results)
    
    # Prepare detailed summary for LLM with per-covariate SMD analysis
    summary_lines = []
    summary_lines.append("# Matching Methods Comparison for Causal Inference")
    summary_lines.append("")
    summary_lines.append("You are a biostatistician expert comparing 4 matching methods.")
    summary_lines.append("Analyze the following results and select the BEST method with detailed reasoning.")
    summary_lines.append("")
    
    # Overall metrics
    summary_lines.append("## Overall Balance Metrics")
    summary_lines.append("")
    for method_name, result in comparison_results.items():
        summary_lines.append(f"### {method_name.upper()}")
        summary_lines.append(f"- N matched pairs: {result['n_matched']}")
        summary_lines.append(f"- Mean SMD across all covariates: {result['mean_smd']:.4f}")
        summary_lines.append(f"- Well-balanced covariates (SMD < 0.1): {result['balanced_pct']:.1%}")
        summary_lines.append(f"- Moderately imbalanced (0.1 ≤ SMD < 0.2): {sum(0.1 <= v < 0.2 for v in result['smd_dict'].values())}/{len(result['smd_dict'])}")
        summary_lines.append(f"- Severely imbalanced (SMD ≥ 0.2): {sum(v >= 0.2 for v in result['smd_dict'].values())}/{len(result['smd_dict'])}")
        summary_lines.append("")
    
    # NEW: Baseline Characteristics Comparison
    summary_lines.append("## Baseline Characteristics (Treatment vs Control)")
    summary_lines.append("")
    summary_lines.append("Compare actual baseline values across methods:")
    summary_lines.append("")
    
    for method_name, result in comparison_results.items():
        if 'baseline_stats' in result and result['baseline_stats']:
            summary_lines.append(f"### {method_name.upper()}")
            baseline = result['baseline_stats']
            
            # Show key continuous variables
            summary_lines.append("**Key Continuous Variables:**")
            for var in ['anchor_age', 'lactate', 'temperature', 'heart_rate', 'apache_ii']:
                if var in baseline:
                    summary_lines.append(
                        f"  - {var}: Treatment={baseline[var]['treatment']}, Control={baseline[var]['control']}"
                    )
            
            # Show key comorbidities
            summary_lines.append("**Key Comorbidities:**")
            for var in ['chf', 'mi', 'copd', 'diabetes', 'ventilation']:
                if var in baseline:
                    summary_lines.append(
                        f"  - {var}: Treatment={baseline[var]['treatment']}, Control={baseline[var]['control']}"
                    )
            summary_lines.append("")
    
    # Top 10 worst balanced covariates per method
    summary_lines.append("## Worst Balanced Covariates (Top 5 per Method)")
    summary_lines.append("")
    for method_name, result in comparison_results.items():
        if result['smd_dict']:
            sorted_smds = sorted(result['smd_dict'].items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            summary_lines.append(f"### {method_name.upper()}")
            for var, smd in sorted_smds:
                summary_lines.append(f"  - {var}: SMD = {smd:.4f}")
            summary_lines.append("")
    
    summary_lines.append("## Selection Criteria")
    summary_lines.append("")
    summary_lines.append("1. **Balance Quality**: Lower mean SMD is better (ideally < 0.1)")
    summary_lines.append("2. **Covariate Coverage**: Higher % of well-balanced covariates")
    summary_lines.append("3. **Sample Size**: Sufficient N for statistical power")
    summary_lines.append("4. **Trade-offs**: Balance quality vs. sample size retention")
    summary_lines.append("5. **Critical Covariates**: Check if important confounders are balanced")
    summary_lines.append("")
    summary_lines.append("## Task")
    summary_lines.append("")
    summary_lines.append("**Analyze the baseline characteristics tables above** and select ONE method.")
    summary_lines.append("")
    summary_lines.append("In your analysis, explain:")
    summary_lines.append("1. **Baseline Comparison**: Which method achieved the best balance in actual baseline values?")
    summary_lines.append("   - Look at Treatment vs Control values for key variables")
    summary_lines.append("   - Are continuous variables (age, lactate, APACHE II) similar between groups?")
    summary_lines.append("   - Are comorbidities (CHF, MI, COPD) balanced?")
    summary_lines.append("2. **SMD Performance**: Which method has lowest mean SMD and highest % balanced?")
    summary_lines.append("3. **Critical Confounders**: Which important prognostic factors are well-controlled?")
    summary_lines.append("4. **Trade-offs**: Consider balance quality vs. sample size")
    summary_lines.append("5. **Final Recommendation**: Provide detailed reasoning in 4-6 sentences")
    
    prompt = "\n".join(summary_lines)
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior biostatistician with expertise in causal inference, propensity score methods, and observational study design. Provide detailed, evidence-based analysis citing specific covariates and metrics."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 800
            },
            timeout=30
        )
        
        if response.status_code == 200:
            llm_response = response.json()['choices'][0]['message']['content']
            
            # Extract method name from LLM response
            selected_method = None
            for method_name in comparison_results.keys():
                if method_name.upper() in llm_response.upper():
                    selected_method = method_name
                    break
            
            if selected_method is None:
                logger.warning("Could not parse method from LLM response, using default")
                return _select_best_method_default(comparison_results)
            
            return selected_method, llm_response
        else:
            logger.warning(f"LLM API returned status {response.status_code}, using default")
            return _select_best_method_default(comparison_results)
    
    except Exception as e:
        logger.warning(f"LLM selection failed: {e}, using default")
        return _select_best_method_default(comparison_results)


def _select_best_method_default(comparison_results: Dict[str, Dict]) -> Tuple[str, str]:
    """
    Default method selection based on mean SMD and balance percentage.
    
    Args:
        comparison_results: Output from compare_all_methods()
    
    Returns:
        Tuple of (selected_method_name, reasoning_text)
    """
    # Rank by mean SMD (lower is better)
    ranked = sorted(
        comparison_results.items(),
        key=lambda x: (x[1]['mean_smd'], -x[1]['balanced_pct'])
    )
    
    best_method = ranked[0][0]
    best_result = ranked[0][1]
    
    reasoning = (
        f"Selected {best_method.upper()} (default rule-based selection). "
        f"Mean SMD: {best_result['mean_smd']:.4f}, "
        f"Balanced: {best_result['balanced_pct']:.1%}, "
        f"N matched: {best_result['n_matched']}. "
        f"This method achieved the lowest mean SMD among all compared methods."
    )
    
    return best_method, reasoning
