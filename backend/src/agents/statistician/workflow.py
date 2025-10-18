"""PSM + Survival Analysis Workflow.

This module provides the PSMSurvivalWorkflow class that orchestrates
statistical analysis combining Propensity Score Matching with Survival Analysis.

Workflow stages:
    1. Load cohort data with baseline characteristics
    2. Perform PSM to create balanced treatment/control groups
    3. Assess balance quality (SMD < 0.1)
    4. Conduct survival analysis (Kaplan-Meier + Cox regression)
    5. Generate publication-ready outputs (tables, figures, summaries)

Outputs:
    - matched_data_*.csv: Matched cohort data
    - baseline_table_*_JAMA.md: Table 1 for publication
    - *_analysis_smd_plot.png: JAMA-style SMD balance plots
    - *_cumulative_mortality.png: Kaplan-Meier curves with risk tables
    - *_survival_summary.csv: HR, CI, p-values
    - balance_assessment_*.csv: SMD reports
    - comparative_summary.md: Main vs sensitivity comparison

Following clean code principles:
- Single Responsibility: Workflow only orchestrates, delegates to specialists
- Dependency Injection: All paths configurable
- YAGNI: No premature optimization
"""

import logging
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd
import yaml

from agents.statistician.analysis.baseline_comparison import (
    generate_baseline_table,
    assess_balance_psm as assess_balance,
)
from agents.statistician.analysis.propensity_score_matching import (
    perform_psm,
)
from agents.statistician.analysis.survival_analysis import (
    perform_survival_analysis_unified,
    create_survival_plot,
)
from agents.statistician.analysis.visualization import (
    generate_smd_plot,
    generate_love_plot_before_after,
    generate_mortality_curve_with_risk_table,
)
from agents.statistician.analysis.multi_method_matching import (
    MultiMethodMatcher,
    select_best_method_with_llm,
)
from pipeline.plugins.estimators.causal_forest import CausalForestEstimator

logger = logging.getLogger(__name__)


class PSMSurvivalWorkflow:
    """PSM + Survival Analysis Workflow orchestrator.

    This class manages the complete PSM analysis pipeline, coordinating
    multiple statistical modules to produce publication-ready results.

    Attributes:
        project_dir: Root directory for cohort data
        data_csv: Cohort CSV filename (must include baseline characteristics)
        config_path: Path to baseline_characteristics.yaml (optional)
        output_dir: Output directory (auto-created)
    """

    def __init__(
        self,
        project_dir: str,
        data_csv: str,
        config_path: Optional[str] = None,
    ):
        """Initialize PSM Survival Workflow.

        Args:
            project_dir: Project directory (e.g., "project/NCT03389555/cohorts/hydrocortisonenasucc")
            data_csv: Data CSV filename with baseline characteristics
            config_path: Path to baseline config YAML (uses default if None)

        Raises:
            FileNotFoundError: If data_csv doesn't exist
            ValueError: If data_csv doesn't contain baseline characteristics
        """
        self.project_dir = Path(project_dir)
        self.data_csv = data_csv
        self.data_path = self.project_dir / data_csv
        self.progress_callback: Optional[Callable[[str], None]] = None

        # Causal Forest results storage
        self._causal_forest_summary: Optional[dict] = None
        self._causal_forest_matched_df: Optional[pd.DataFrame] = None
        
        # Multi-method matching results storage
        self._method_comparison_results: Optional[Dict] = None
        self._selected_method: Optional[str] = None
        self._method_selection_reasoning: Optional[str] = None

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Cohort data not found: {self.data_path}\n"
                f"Ensure Phase 2→3 completed successfully."
            )

        # Output directory
        self.output_dir = self.project_dir / "outputs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default config path
            self.config_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "config"
                / "metadata"
                / "baseline_characteristics.yaml"
            )

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f)

        logger.info(f"Initialized PSMSurvivalWorkflow")
        logger.info(f"  Data: {self.data_path}")
        logger.info(f"  Output: {self.output_dir}")
        logger.info(f"  Config: {self.config_path}")

    def set_progress_callback(self, callback: Callable[[str], None]):
        """Set the progress callback function for real-time updates."""
        self.progress_callback = callback

    def _report_progress(self, message: str):
        """Helper to safely call the progress callback if it exists."""
        if self.progress_callback:
            self.progress_callback(message)

    def run(self) -> int:
        """Execute complete PSM + Survival Analysis workflow.

        This method orchestrates all analysis steps in sequence:
        1. Load and validate data
        2. Run PSM analysis (comprehensive with all available variables)
        3. Generate all outputs (tables, figures, summaries)

        Returns:
            0 if successful, 1 if error occurred

        Side effects:
            Creates output files in self.output_dir
        """
        try:
            logger.info("=" * 80)
            logger.info("PSM + SURVIVAL ANALYSIS WORKFLOW")
            logger.info("=" * 80)

            # Load data
            self._report_progress("Running PSM: Loading cohort data...")

            # Ensure minimum display time for progress indicator (1.5 seconds)
            time.sleep(1.5)

            logger.info("\n[1/3] Loading cohort data...")

            # ✅ Use load_baseline_characteristics for automatic type conversion
            import sys
            from pathlib import Path as P
            scripts_path = P(__file__).parents[3] / "scripts"
            if str(scripts_path) not in sys.path:
                sys.path.insert(0, str(scripts_path))

            try:
                from feature_types_utils import load_baseline_characteristics
                df = load_baseline_characteristics(str(self.data_path))
                logger.info(f"  ✅ Loaded {len(df):,} patients with automatic feature type conversion")
            except ImportError:
                logger.warning("  ⚠️ feature_types_utils not found, using standard pd.read_csv()")
                df = pd.read_csv(self.data_path)
                logger.info(f"  Loaded {len(df):,} patients")

            # Validate required columns
            required_cols = ["subject_id", "treatment_group", "mortality"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Run comprehensive PSM analysis
            self._report_progress("Running PSM: Performing propensity score matching...")
            logger.info("\n[2/3] Running PSM analysis with comprehensive variable set...")
            self._run_main_analysis(df)

            logger.info("\n[3/3] ✅ Workflow completed successfully!")
            logger.info(f"\nGenerated {len(list(self.output_dir.glob('*')))} files in: {self.output_dir}")

            # Generate and save LLM summary
            self._generate_and_save_llm_summary(df)

            return 0

        except Exception as e:
            logger.exception("Workflow failed with exception")
            self._report_progress("Workflow failed with an error.")
            return 1

    def _run_main_analysis(self, df: pd.DataFrame) -> None:
        """Run comprehensive PSM analysis with all available variables.

        Includes all baseline characteristics for matching.
        Now compares multiple matching methods and selects the best one.

        Args:
            df: Full cohort dataframe
        """
        # Select variables (include all available)
        baseline_vars = self._get_baseline_variables(df, exclude_threshold=20.0)
        logger.info(f"  Selected {len(baseline_vars)} variables for matching")

        # ========== NEW: Multi-Method Comparison ==========
        # Step 1: Run 4 matching algorithms
        self._report_progress("Step 1/6: Running 4 matching algorithms (PSM, PSM+caliper, Mahalanobis, IPTW)...")
        logger.info("\n[Step 1/6] Running 4 matching algorithms...")
        
        matcher = MultiMethodMatcher(df, baseline_vars)
        
        # First, just do the matching (not baseline extraction yet)
        logger.info("  Executing PSM (no caliper)...")
        psm_matched = matcher.match_psm(caliper=None)
        
        logger.info("  Executing PSM with caliper=0.01...")
        psm_caliper_matched = matcher.match_psm(caliper=0.01)
        
        logger.info("  Executing Mahalanobis matching...")
        mahal_matched = matcher.match_mahalanobis()
        
        logger.info("  Executing IPTW weighting...")
        iptw_df = matcher.apply_iptw()
        
        logger.info(f"  Completed all 4 matching methods")
        
        # Step 2: Extract baseline characteristics for each method
        self._report_progress("Step 2/6: Extracting baseline characteristics for each method...")
        logger.info("\n[Step 2/6] Extracting baseline characteristics...")
        
        comparison_results = {}
        for method_name, matched_df in [
            ('psm', psm_matched),
            ('psm_caliper', psm_caliper_matched), 
            ('mahalanobis', mahal_matched),
            ('iptw', iptw_df)
        ]:
            logger.info(f"  Extracting baseline for {method_name}...")
            
            # Calculate SMD
            if method_name == 'iptw':
                smd_dict = matcher.calculate_smd_for_method(matched_df, iptw_weights=matched_df['iptw_weight'].values)
            else:
                smd_dict = matcher.calculate_smd_for_method(matched_df)
            
            # Extract baseline stats
            baseline_stats = matcher._extract_baseline_stats(matched_df, method_name)
            
            comparison_results[method_name] = {
                'matched_df': matched_df,
                'smd_dict': smd_dict,
                'mean_smd': np.mean(list(smd_dict.values())) if smd_dict and len(smd_dict) > 0 else np.nan,
                'balanced_pct': sum(v < 0.1 for v in smd_dict.values()) / len(smd_dict) if smd_dict and len(smd_dict) > 0 else 0.0,
                'n_matched': len(matched_df) // 2 if method_name != 'iptw' and len(matched_df) > 0 else len(matched_df),
                'baseline_stats': baseline_stats
            }
            
            mean_smd = comparison_results[method_name]['mean_smd']
            mean_smd_str = f"{mean_smd:.4f}" if not np.isnan(mean_smd) else "N/A"
            logger.info(f"    {method_name}: mean_smd={mean_smd_str}")
        
        logger.info(f"  Completed baseline extraction for all methods")
        
        # Store comparison results
        self._method_comparison_results = comparison_results
        
        # Generate comparison summary
        summary_text = matcher.generate_comparison_summary(comparison_results)
        logger.info("\n" + summary_text)
        
        # Save comparison results to file
        comparison_path = self.output_dir / "method_comparison_summary.txt"
        with open(comparison_path, 'w') as f:
            f.write(summary_text)
        logger.info(f"  Saved method comparison: {comparison_path}")
        
        # Step 3: LLM comparison and selection
        self._report_progress("Step 3/6: Using LLM to compare baseline characteristics and select best method...")
        logger.info("\n[Step 3/6] LLM analyzing baseline characteristics...")
        selected_method, reasoning = select_best_method_with_llm(
            comparison_results, 
            baseline_vars
        )
        
        self._selected_method = selected_method
        self._method_selection_reasoning = reasoning
        
        logger.info(f"\n[LLM Selection] Best method: {selected_method.upper()}")
        logger.info(f"[LLM Reasoning] {reasoning}")
        
        # Save LLM reasoning
        reasoning_path = self.output_dir / "method_selection_reasoning.txt"
        with open(reasoning_path, 'w') as f:
            f.write(f"Selected Method: {selected_method.upper()}\n\n")
            f.write(f"Reasoning:\n{reasoning}\n")
        logger.info(f"  Saved LLM reasoning: {reasoning_path}")
        
        # Use the selected method's matched dataset
        matched_df = comparison_results[selected_method]['matched_df']
        
        # DEBUG: Log matched_df size
        n_treat_matched = (matched_df['treatment_group'] == 1).sum()
        n_ctrl_matched = (matched_df['treatment_group'] == 0).sum()
        logger.info(f"\n[Matched Dataset] Method: {selected_method}")
        logger.info(f"  Total subjects: {len(matched_df)}")
        logger.info(f"  Treatment: {n_treat_matched}")
        logger.info(f"  Control: {n_ctrl_matched}")
        logger.info(f"  Expected: {n_treat_matched} pairs (1:1 matching)")
        
        # Save matched data
        matched_path = self.output_dir / f"matched_data_main_{selected_method}.csv"
        matched_df.to_csv(matched_path, index=False)
        logger.info(f"  Saved matched data ({selected_method}): {matched_path}")

        # Step 4: Assess balance
        self._report_progress("Step 4/6: Assessing covariate balance...")
        logger.info("\n[Step 4/6] Assessing balance...")
        balance_df = assess_balance(
            original_df=df,
            matched_df=matched_df,
            variables=baseline_vars,
        )
        balance_path = self.output_dir / "balance_assessment_main.csv"
        balance_df.to_csv(balance_path, index=False)
        logger.info(f"  Balance: {(balance_df['post_smd'] < 0.1).sum()}/{len(balance_df)} variables balanced")

        # Generate Love Plot (Before/After comparison - academically rigorous)
        love_plot_path = self.output_dir / "main_analysis_love_plot.png"
        generate_love_plot_before_after(
            original_df=df,
            matched_df=matched_df,
            variables=baseline_vars,
            output_path=love_plot_path,
            analysis_type="main"
        )
        logger.info(f"  Generated Love Plot (Before/After): {love_plot_path}")

        # Step 5: Generate baseline table
        self._report_progress("Step 5/6: Generating baseline characteristics table (Table 1)...")
        logger.info("\n[Step 5/6] Generating Table 1...")
        table_path = self.output_dir / "baseline_table_main_JAMA.md"
        generate_baseline_table(
            matched_df=matched_df,
            variables=baseline_vars,
            output_path=table_path,
            original_df=df,  # ← NEW: Pass original cohort for before/after comparison
            style="JAMA",
        )
        logger.info(f"  Generated Table 1 (Before/After comparison): {table_path}")

        # Step 6: Survival analysis
        self._report_progress("Step 6/6: Analyzing survival outcomes (Kaplan-Meier + Cox regression)...")
        logger.info("\n[Step 6/6] Running survival analysis...")
        survival_results = perform_survival_analysis_unified(
            df=matched_df,
            time_column="outcome_days",  # Use actual time-to-event column
            event_column="mortality",
            group_column="treatment_group",
            output_dir=str(self.output_dir)
        )

        # Extract clean numeric results from survival analysis
        cox_model = survival_results.get('cox_model', {})
        hr_val = float(cox_model.get('hr', 0)) if cox_model.get('hr') is not None else None

        # Extract CI bounds
        ci = cox_model.get('ci')
        ci_lower = float(ci.iloc[0]) if ci is not None and len(ci) > 0 else None
        ci_upper = float(ci.iloc[1]) if ci is not None and len(ci) > 1 else None

        # Extract p-value
        pval = float(cox_model.get('p_value', 1)) if cox_model.get('p_value') is not None else None

        # Calculate mortality rates
        n_treatment = (matched_df[self.config.get('treatment_col', 'treatment_group')] == 1).sum()
        n_control = (matched_df[self.config.get('treatment_col', 'treatment_group')] == 0).sum()
        mortality_treatment = matched_df[matched_df[self.config.get('treatment_col', 'treatment_group')] == 1]['mortality'].mean()
        mortality_control = matched_df[matched_df[self.config.get('treatment_col', 'treatment_group')] == 0]['mortality'].mean()

        # Save clean survival summary
        clean_summary = {
            'analysis_type': 'main',
            'n_treatment': n_treatment,
            'n_control': n_control,
            'mortality_treatment': mortality_treatment,
            'mortality_control': mortality_control,
            'cox_hr': hr_val,
            'cox_ci_lower': ci_lower,
            'cox_ci_upper': ci_upper,
            'cox_pvalue': pval
        }

        summary_path = self.output_dir / "main_survival_summary.csv"
        pd.DataFrame([clean_summary]).to_csv(summary_path, index=False)

        # Format HR and p-value for logging
        hr_str = f"{hr_val:.3f}" if hr_val is not None else "N/A"
        pval_str = f"{pval:.4f}" if pval is not None else "N/A"
        logger.info(f"  HR: {hr_str} (95% CI: {ci_lower:.3f}-{ci_upper:.3f}, p={pval_str})")

        # Create JAMA-style mortality curve with risk table and HR
        plot_path = self.output_dir / "main_analysis_cumulative_mortality.png"
        
        # Delete old plot if exists to ensure fresh generation
        if plot_path.exists():
            plot_path.unlink()
            logger.info(f"  Deleted old mortality curve plot")
        
        # Prepare Cox results for plot
        cox_results = {
            'hr': hr_val,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'p_value': pval
        }
        
        generate_mortality_curve_with_risk_table(
            matched_df=matched_df,
            output_path=plot_path,
            analysis_type="main",
            time_col="outcome_days",
            event_col="mortality",
            cox_results=cox_results
        )
        logger.info(f"  Generated JAMA-style mortality curve with HR: {plot_path}")

        # Causal Forest Analysis (Heterogeneous Treatment Effects)
        self._report_progress("Running Causal Forest: Estimating treatment effect heterogeneity...")
        logger.info("\n  Running Causal Forest Analysis...")

        # Ensure minimum display time for progress indicator (300ms)
        time.sleep(0.3)

        try:
            cf_estimator = CausalForestEstimator(
                treatment="treatment_group",
                outcome="mortality",
                covariates=[],  # No W (confounders), PSM already balanced
                effect_modifiers=baseline_vars,  # Use all baseline vars as effect modifiers
                n_estimators=100,
                min_samples_leaf=10,
                random_state=42
            )
            cf_estimator.fit(matched_df)
            cf_results = cf_estimator.estimate_effect()

            # Add CATE values to matched dataframe (only for complete cases)
            # Initialize with NaN for all rows
            matched_df["cate_value"] = float('nan')
            # Fill in CATE values for complete cases using the mask from estimator
            if hasattr(cf_estimator, '_mask'):
                matched_df.loc[cf_estimator._mask, "cate_value"] = cf_results["cate_estimates"]
            else:
                # Fallback: assume all rows were used
                matched_df["cate_value"] = cf_results["cate_estimates"]

            # Save updated matched data with CATE
            matched_path = self.output_dir / "matched_data_main.csv"
            matched_df.to_csv(matched_path, index=False)

            # Calculate summary statistics
            cate_values = cf_results["cate_estimates"]
            cf_summary = {
                "ate": float(cf_results["ate"]),
                "mean_cate": float(pd.Series(cate_values).mean()),
                "cate_std": float(pd.Series(cate_values).std()),
                "cate_range": [float(pd.Series(cate_values).min()), float(pd.Series(cate_values).max())],
                "positive_response_rate": float((pd.Series(cate_values) > 0).mean()),
                "feature_importances": cf_results["feature_importances"]
            }

            # Store for agent result
            self._causal_forest_summary = cf_summary
            self._causal_forest_matched_df = matched_df

            logger.info(f"  ✅ Causal Forest completed successfully")
            logger.info(f"  📊 ATE: {cf_summary['ate']:.3f}")
            logger.info(f"  📈 CATE range: [{cf_summary['cate_range'][0]:.3f}, {cf_summary['cate_range'][1]:.3f}]")
            logger.info(f"  🎯 Positive response rate: {cf_summary['positive_response_rate']*100:.1f}%")
            logger.info(f"  🌲 Top 3 important features: {list(cf_summary['feature_importances'].items())[:3]}")

        except Exception as e:
            logger.warning(f"  Causal Forest analysis failed: {e}")
            self._causal_forest_summary = None
            self._causal_forest_matched_df = None

    def _get_baseline_variables(
        self, df: pd.DataFrame, exclude_threshold: float
    ) -> list[str]:
        """Select baseline variables for PSM.

        Args:
            df: Cohort dataframe
            exclude_threshold: Exclude variables with missingness > this %

        Returns:
            List of variable names for PSM
        """
        # Calculate missingness
        missing_pct = (df.isnull().sum() / len(df) * 100)

        # Exclude columns
        excluded_cols = {
            "subject_id",
            "hadm_id",
            "stay_id",
            "treatment_group",
            "mortality",
        }

        # Select numeric variables below threshold
        baseline_vars = []
        for col in df.select_dtypes(include=["number"]).columns:
            if col not in excluded_cols and missing_pct[col] <= exclude_threshold:
                baseline_vars.append(col)

        return baseline_vars

    def get_causal_forest_results(self) -> tuple[Optional[dict], Optional[pd.DataFrame]]:
        """Get Causal Forest analysis results.

        Returns:
            Tuple of (summary_dict, matched_df_with_cate) or (None, None) if not computed
        """
        return self._causal_forest_summary, self._causal_forest_matched_df

    def generate_llm_summary(
        self,
        nct_id: str,
        medication: str,
        cohort_summary: dict,
        main_analysis: dict,
        sensitivity_analysis: Optional[dict] = None
    ) -> dict:
        """Generate LLM-based structured summary of analysis results.

        Args:
            nct_id: Clinical trial NCT ID
            medication: Medication name
            cohort_summary: Cohort summary dict
            main_analysis: Main analysis results dict
            sensitivity_analysis: Optional sensitivity analysis results

        Returns:
            Dictionary with question, conclusion, population, intervention, findings
        """
        from agents.statistician.analysis.result_summarizer import generate_analysis_summary

        try:
            summary = generate_analysis_summary(
                nct_id=nct_id,
                medication=medication,
                cohort_summary=cohort_summary,
                main_analysis=main_analysis,
                sensitivity_analysis=sensitivity_analysis
            )
            logger.info("Generated LLM-based analysis summary")
            return summary
        except Exception as e:
            logger.exception(f"Failed to generate LLM summary: {e}")
            return {}

    def _generate_and_save_llm_summary(self, df: pd.DataFrame) -> None:
        """Generate and save LLM summary to file during workflow execution.

        Reads survival summary CSV, generates LLM summary, and saves to JSON file.

        Args:
            df: Full cohort dataframe (used for cohort summary stats)
        """
        try:
            import json
            from rwe_api.config import settings

            logger.info("\n[LLM Summary] Generating executive summary...")

            # Read survival summary CSV for real data
            survival_csv = self.output_dir / "main_survival_summary.csv"

            if not survival_csv.exists():
                logger.warning(f"  Survival CSV not found: {survival_csv}, skipping LLM summary")
                return

            survival_df = pd.read_csv(survival_csv)
            if len(survival_df) == 0:
                logger.warning("  Survival CSV is empty, skipping LLM summary")
                return

            row = survival_df.iloc[0]
            cox_hr = float(row['cox_hr'])
            cox_ci_lower = float(row['cox_ci_lower'])
            cox_ci_upper = float(row['cox_ci_upper'])
            cox_pvalue = float(row['cox_pvalue'])
            mortality_treatment_pct = float(row['mortality_treatment']) * 100
            mortality_control_pct = float(row['mortality_control']) * 100
            n_matched = int(row['n_treatment'])

            # Build cohort summary
            n_treatment = (df['treatment_group'] == 1).sum()
            n_control = (df['treatment_group'] == 0).sum()
            total_patients = len(df)

            cohort_summary = {
                "total_patients": total_patients,
                "treatment_n": n_treatment,
                "control_n": n_control,
                "treatment_pct": (n_treatment / total_patients * 100) if total_patients > 0 else 0,
            }

            # Build main analysis dict
            main_analysis = {
                "matched_pairs": n_matched,
                "hazard_ratio": cox_hr,
                "ci_95_lower": cox_ci_lower,
                "ci_95_upper": cox_ci_upper,
                "p_value": cox_pvalue,
                "mortality_treatment_pct": mortality_treatment_pct,
                "mortality_control_pct": mortality_control_pct,
            }

            # Extract NCT ID and medication from project path
            # project_dir format: project/NCT03389555/cohorts/hydrocortisonenasucc
            parts = str(self.project_dir).split('/')
            nct_id = None
            medication = None

            for i, part in enumerate(parts):
                if part.startswith('NCT'):
                    nct_id = part
                if i > 0 and parts[i-1] == 'cohorts':
                    medication = part

            if not nct_id or not medication:
                logger.warning(f"  Could not extract NCT ID or medication from path: {self.project_dir}")
                nct_id = "NCT00000000"
                medication = "unknown"

            # Generate LLM summary
            from agents.statistician.analysis.result_summarizer import generate_analysis_summary

            llm_summary = generate_analysis_summary(
                nct_id=nct_id,
                medication=medication,
                cohort_summary=cohort_summary,
                main_analysis=main_analysis,
                sensitivity_analysis=None,
                openrouter_api_key=settings.OPENROUTER_API_KEY
            )

            # Save to JSON file in analysis_output directory
            analysis_output_dir = self.project_dir / "analysis_output"
            analysis_output_dir.mkdir(parents=True, exist_ok=True)

            llm_summary_path = analysis_output_dir / "llm_summary.json"
            with open(llm_summary_path, 'w') as f:
                json.dump(llm_summary, f, indent=2)

            logger.info(f"  ✅ Saved LLM summary: {llm_summary_path}")

        except Exception as e:
            logger.exception(f"  Failed to generate/save LLM summary: {e}")
            # Don't fail the workflow if LLM summary fails
