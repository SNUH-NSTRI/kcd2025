"""LangGraph workflow for Statistician Agent.

This module defines the LangGraph state machine that orchestrates
PSM (Propensity Score Matching) analysis with LLM-powered decision making.

Workflow:
    1. analyze_baseline: Load cohort, calculate SMD, assess missingness
    2. recommend_params: LLM recommends PSM parameters based on data characteristics
    3. execute_psm: Run PSM + Survival Analysis workflow
    4. interpret_results: LLM interprets results and generates report

Following clean code principles from vooster-docs/clean-code.md:
- Logging instead of print statements
- Configurable dependencies (no hardcoded paths)
- Pure functions with no side effects
- Single Responsibility Principle
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, Sequence, TypedDict

import numpy as np
import pandas as pd
import yaml
from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


# ============================================================================
# State Definition
# ============================================================================


class StatisticianState(TypedDict):
    """State for statistician LangGraph workflow.

    This TypedDict defines all data passed between nodes in the workflow.
    Following the principle of explicit contracts.
    """

    messages: Annotated[Sequence[BaseMessage], "Conversation history"]
    cohort_path: str
    output_dir: str

    # Data analysis results
    cohort_summary: dict
    baseline_imbalance: dict
    missingness_report: dict

    # PSM parameters (recommended by LLM)
    psm_params: dict

    # Execution results
    psm_results: dict
    survival_results: dict

    # Causal Forest results (optional)
    causal_forest_summary: Optional[dict]
    causal_forest_outcomes: Optional[list]
    
    # NEW: Multi-method matching results
    method_comparison_results: Optional[dict]
    selected_method: Optional[str]
    method_selection_reasoning: Optional[str]

    # Final report
    interpretation: str
    next_action: str

    # Configuration
    prompts: dict
    openrouter_api_key: str

    # Progress callback (optional)
    progress_callback: Optional[callable]


# ============================================================================
# Prompt Template Utilities
# ============================================================================


def load_prompt_templates(prompts_file: Optional[Path] = None) -> dict:
    """Load prompt templates from YAML file.

    Args:
        prompts_file: Path to prompts YAML. If None, uses default location.

    Returns:
        Dictionary containing prompt templates and configuration.

    Raises:
        FileNotFoundError: If prompts file doesn't exist.
        yaml.YAMLError: If YAML is malformed.
    """
    if prompts_file is None:
        # Default path - relative to this file
        prompts_file = (
            Path(__file__).parent.parent.parent.parent.parent
            / "config"
            / "prompts"
            / "statistician_prompts.yaml"
        )

    logger.info(f"Loading prompt templates from {prompts_file}")

    if not prompts_file.exists():
        raise FileNotFoundError(f"Prompts file not found: {prompts_file}")

    with open(prompts_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================================
# Node 1: Baseline Data Analysis
# ============================================================================


def analyze_baseline_node(state: StatisticianState) -> StatisticianState:
    """Node 1: Analyze baseline data characteristics.

    This node performs statistical analysis of the cohort data:
    - Cohort size and treatment/control distribution
    - Pre-matching Standardized Mean Difference (SMD)
    - Missingness patterns

    Args:
        state: Current workflow state with cohort_path.

    Returns:
        Updated state with cohort_summary, baseline_imbalance, missingness_report.

    Raises:
        FileNotFoundError: If cohort CSV doesn't exist.
        pd.errors.EmptyDataError: If CSV is empty.
    """
    logger.info("=" * 70)
    logger.info("NODE 1: DATA PREPARATION FOR PSM")
    logger.info("=" * 70)

    # Report progress
    progress_callback = state.get("progress_callback")
    if progress_callback:
        progress_callback("Running PSM: Loading and preparing cohort data...")

    cohort_path = Path(state["cohort_path"])

    # ✅ Use load_baseline_characteristics for automatic type conversion
    # Import at runtime to avoid circular dependency
    import sys
    from pathlib import Path as P

    # Correct path: backend/src/agents/statistician/graph.py -> project_root/scripts/
    scripts_path = P(__file__).parents[4] / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))

    try:
        from feature_types_utils import load_baseline_characteristics
        df = load_baseline_characteristics(str(cohort_path))
        logger.info(f"✅ Loaded cohort data with automatic feature type conversion from {scripts_path}")
    except ImportError as e:
        # Fallback to standard read_csv if feature_types_utils not available
        logger.warning(f"⚠️ feature_types_utils not found at {scripts_path}: {e}")
        logger.warning("Using standard pd.read_csv() without type conversion")
        df = pd.read_csv(cohort_path)

    treatment = df[df["treatment_group"] == 1]
    control = df[df["treatment_group"] == 0]

    # Cohort summary
    cohort_summary = {
        "total_patients": len(df),
        "treatment_n": len(treatment),
        "control_n": len(control),
        "treatment_pct": len(treatment) / len(df) * 100 if len(df) > 0 else 0,
        "mortality_overall": (
            df["mortality"].mean() * 100 if "mortality" in df.columns else None
        ),
    }

    logger.info(
        f"Cohort: {cohort_summary['total_patients']:,} patients "
        f"({cohort_summary['treatment_n']:,} treatment, {cohort_summary['control_n']:,} control)"
    )

    # Calculate pre-matching SMD for all baseline covariates
    # Following clinical research best practices: include ALL pre-treatment covariates
    # that were/should be in the propensity score model

    # Exclude variables that should NOT be in PSM:
    # - Identifiers (subject_id, hadm_id, stay_id)
    # - Treatment indicator (treatment_group)
    # - Outcome variables (mortality, death_28d, survival_time_28d, etc.)
    # - Post-treatment timestamps (icu_outtime, date_of_death)
    # - Post-treatment measures (*_days variables)

    exclude_vars = {
        "subject_id", "hadm_id", "stay_id",  # Identifiers
        "treatment_group", "treat",  # Treatment indicator
        "mortality", "death_28d", "survival_time_28d", "outcome_days",  # Outcomes
        "icu_outtime", "date_of_death", "dod",  # Post-treatment timestamps
        "days_to_death", "los",  # Post-treatment durations
    }

    # Get all numeric columns (continuous, binary, ordinal)
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    # Include numeric baseline covariates
    baseline_vars = [
        col for col in numeric_cols
        if col not in exclude_vars
    ]

    # ⭐ CRITICAL: Add categorical variables (gender, race)
    # Gender is already binary (0/1) - can use directly
    if "gender" in df.columns and "gender" not in baseline_vars:
        baseline_vars.append("gender")

    # Race: One-hot encode for SMD calculation
    # Each category becomes a separate covariate (standard practice in PSM)
    race_dummies = []
    if "race" in df.columns:
        # Get unique race categories
        race_categories = df["race"].dropna().unique()
        if len(race_categories) > 1:
            # One-hot encode, drop first category as reference
            race_encoded = pd.get_dummies(df["race"], prefix="race", drop_first=True)
            race_dummies = race_encoded.columns.tolist()

            # Add encoded columns to treatment and control dataframes
            treatment = pd.concat([treatment, race_encoded.loc[treatment.index]], axis=1)
            control = pd.concat([control, race_encoded.loc[control.index]], axis=1)

            # Add to baseline_vars for SMD calculation
            baseline_vars.extend(race_dummies)
            logger.info(f"✓ Race one-hot encoded: {len(race_dummies)} categories added")

    smd_results = []
    for var in baseline_vars:
        if var in df.columns:
            t_data = treatment[var].dropna()
            c_data = control[var].dropna()

            if len(t_data) > 0 and len(c_data) > 0:
                if not pd.api.types.is_numeric_dtype(t_data):
                    logger.debug(f"Skipping non-numeric variable for SMD calculation: {var} (dtype: {t_data.dtype})")
                    continue

                t_mean = t_data.mean()
                t_std = t_data.std()
                c_mean = c_data.mean()
                c_std = c_data.std()

                pooled_std = np.sqrt((t_std**2 + c_std**2) / 2)
                smd = abs((t_mean - c_mean) / pooled_std) if pooled_std > 0 else 0

                smd_results.append(
                    {
                        "variable": var,
                        "smd": smd,
                        "treatment_mean": t_mean,
                        "control_mean": c_mean,
                        "imbalanced": smd > 0.1,
                    }
                )

    smd_df = pd.DataFrame(smd_results).sort_values("smd", ascending=False)

    baseline_imbalance = {
        "total_variables": len(smd_df),
        "imbalanced_vars": len(smd_df[smd_df["smd"] > 0.1]),
        "max_smd": smd_df["smd"].max() if len(smd_df) > 0 else 0,
        "median_smd": smd_df["smd"].median() if len(smd_df) > 0 else 0,
        "top_imbalanced": smd_df.head(10).to_dict("records") if len(smd_df) > 0 else [],
    }

    logger.info(
        f"Pre-matching imbalance: {baseline_imbalance['imbalanced_vars']}/{baseline_imbalance['total_variables']} "
        f"variables (max SMD: {baseline_imbalance['max_smd']:.3f})"
    )

    # Missingness analysis
    missing_pct = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    high_missing = missing_pct[missing_pct > 20]

    missingness_report = {
        "high_missing_count": len(high_missing),
        "high_missing_vars": high_missing.to_dict(),
        "median_missing_pct": missing_pct.median(),
    }

    logger.info(
        f"Missingness: {missingness_report['high_missing_count']} variables >20% missing "
        f"(median: {missingness_report['median_missing_pct']:.1f}%)"
    )

    state["cohort_summary"] = cohort_summary
    state["baseline_imbalance"] = baseline_imbalance
    state["missingness_report"] = missingness_report

    return state


# ============================================================================
# Node 2: PSM Parameter Recommendation
# ============================================================================


def recommend_psm_params_node(state: StatisticianState) -> StatisticianState:
    """Node 2: Use default PSM parameters (LLM recommendation disabled).

    Previously used GPT-4o-mini to recommend PSM parameters, but now uses
    fixed default values to avoid LLM dependency and ensure consistency.

    Default parameters:
    - Caliper size: 0.2 × SD (standard in literature)
    - Matching ratio: 1:1 (nearest neighbor)
    - Variable selection: exclude variables with >20% missing data
    - Missingness threshold: 20%

    Args:
        state: Current state with baseline analysis results.

    Returns:
        Updated state with psm_params.
    """
    logger.info("=" * 70)
    logger.info("NODE 2: PSM PARAMETER SETUP (Using Defaults)")
    logger.info("=" * 70)

    # Report progress
    progress_callback = state.get("progress_callback")
    if progress_callback:
        progress_callback("Setting PSM parameters to defaults...")

    # Use default parameters (no LLM call)
    psm_params = {
        "caliper_multiplier": 0.2,
        "matching_ratio": "1:1",
        "variable_selection_strategy": "exclude_high_missing",
        "exclude_threshold_pct": 20.0,
        "rationale": "Using standard default parameters (caliper=0.2×SD, 1:1 matching)",
    }

    logger.info(
        f"Default parameters: caliper={psm_params['caliper_multiplier']}×SD, "
        f"matching={psm_params['matching_ratio']}, "
        f"strategy={psm_params['variable_selection_strategy']}"
    )

    state["psm_params"] = psm_params

    # COMMENTED OUT: LLM-based parameter recommendation
    # The following code was used to query GPT-4o-mini for optimal PSM parameters
    # but has been disabled to reduce LLM dependencies and ensure deterministic results.
    #
    # if not state.get("openrouter_api_key"):
    #     raise ValueError("OPENROUTER_API_KEY not provided in state")
    #
    # prompts = state.get("prompts", {})
    #
    # # Initialize OpenRouter-connected LLM
    # llm = ChatOpenAI(
    #     model=prompts.get("config", {}).get("model", {}).get("default", "openai/gpt-4o-mini"),
    #     openai_api_key=state["openrouter_api_key"],
    #     openai_api_base="https://openrouter.ai/api/v1",
    #     temperature=prompts.get("config", {})
    #     .get("temperature", {})
    #     .get("parameter_recommendation", 0.7),
    # )
    #
    # # Prepare context from YAML template
    # template = (
    #     prompts.get("prompts", {})
    #     .get("parameter_recommendation", {})
    #     .get("template", "Analyze baseline data and recommend PSM parameters")
    # )
    #
    # context = template.format(
    #     total_patients=state["cohort_summary"]["total_patients"],
    #     treatment_n=state["cohort_summary"]["treatment_n"],
    #     treatment_pct=state["cohort_summary"]["treatment_pct"],
    #     control_n=state["cohort_summary"]["control_n"],
    #     control_pct=100 - state["cohort_summary"]["treatment_pct"],
    #     total_variables=state["baseline_imbalance"]["total_variables"],
    #     imbalanced_vars=state["baseline_imbalance"]["imbalanced_vars"],
    #     max_smd=state["baseline_imbalance"]["max_smd"],
    #     median_smd=state["baseline_imbalance"]["median_smd"],
    #     top_imbalanced_json=json.dumps(
    #         state["baseline_imbalance"]["top_imbalanced"][:5], indent=2
    #     ),
    #     high_missing_count=state["missingness_report"]["high_missing_count"],
    #     median_missing_pct=state["missingness_report"]["median_missing_pct"],
    # )
    #
    # system_message = prompts.get("system_messages", {}).get(
    #     "parameter_recommendation", "You are an expert biostatistician."
    # )
    #
    # messages = [SystemMessage(content=system_message), HumanMessage(content=context)]
    #
    # logger.info("Querying GPT-4o-mini for PSM parameter recommendations...")
    #
    # response = llm.invoke(messages)
    # response_text = response.content
    #
    # # Parse JSON response
    # try:
    #     # Extract JSON from response (handle markdown code blocks)
    #     if "```json" in response_text:
    #         json_start = response_text.find("```json") + 7
    #         json_end = response_text.find("```", json_start)
    #         json_text = response_text[json_start:json_end].strip()
    #     elif "```" in response_text:
    #         json_start = response_text.find("```") + 3
    #         json_end = response_text.find("```", json_start)
    #         json_text = response_text[json_start:json_end].strip()
    #     else:
    #         json_text = response_text
    #
    #     psm_params = json.loads(json_text)
    #
    #     logger.info(
    #         f"LLM recommendations: caliper={psm_params['caliper_multiplier']}×SD, "
    #         f"matching={psm_params['matching_ratio']}, "
    #         f"strategy={psm_params['variable_selection_strategy']}"
    #     )
    #
    #     state["psm_params"] = psm_params
    #
    #     # Add to message history
    #     state["messages"].append(HumanMessage(content=context))
    #     state["messages"].append(AIMessage(content=response_text))
    #
    # except json.JSONDecodeError as e:
    #     logger.error(f"Failed to parse LLM response as JSON: {e}")
    #     logger.debug(f"Raw response: {response_text}")
    #
    #     # Fallback to default parameters
    #     psm_params = {
    #         "caliper_multiplier": 0.2,
    #         "matching_ratio": "1:1",
    #         "variable_selection_strategy": "exclude_high_missing",
    #         "exclude_threshold_pct": 20.0,
    #         "rationale": "Using default parameters due to JSON parsing error",
    #     }
    #     state["psm_params"] = psm_params
    #     logger.warning("Falling back to default PSM parameters")

    return state


# ============================================================================
# Node 3: Execute PSM Workflow
# ============================================================================


def execute_psm_workflow_node(state: StatisticianState) -> StatisticianState:
    """Node 3: Execute PSM + Survival Analysis.

    Runs the PSMSurvivalWorkflow with LLM-recommended parameters.
    This node depends on the external workflow module.

    Args:
        state: Current state with cohort_path and psm_params.

    Returns:
        Updated state with psm_results and next_action.

    Note:
        Imports PSMSurvivalWorkflow dynamically to avoid circular dependencies.
    """
    logger.info("=" * 70)
    logger.info("NODE 3: EXECUTING PSM + SURVIVAL ANALYSIS")
    logger.info("=" * 70)

    # Report progress
    progress_callback = state.get("progress_callback")
    if progress_callback:
        progress_callback("Running PSM and survival analysis...")

    # Import here to avoid circular dependency
    # This is acceptable for workflow integration
    try:
        # Try new location first (after integration)
        from agents.statistician.workflow import PSMSurvivalWorkflow
    except ImportError:
        # Fallback to old location (통합필요 folder)
        import sys

        sys.path.insert(
            0,
            str(
                Path(__file__).parent.parent.parent.parent.parent
                / "통합필요"
                / "workflows"
            ),
        )
        from psm_survival_workflow import PSMSurvivalWorkflow

    cohort_path = Path(state["cohort_path"])
    cohort_dir = cohort_path.parent

    # Initialize workflow
    workflow = PSMSurvivalWorkflow(
        project_dir=str(cohort_dir), data_csv=cohort_path.name, config_path=None  # Use default
    )

    # ENHANCEMENT: Pass progress callback for granular updates
    if progress_callback:
        workflow.set_progress_callback(progress_callback)

    # Execute workflow
    logger.info(
        f"Running PSM workflow with caliper={state['psm_params']['caliper_multiplier']}×SD, "
        f"strategy={state['psm_params']['variable_selection_strategy']}"
    )

    result_code = workflow.run()

    if result_code == 0:
        logger.info("PSM + Survival Analysis completed successfully")

        # Load results
        output_dir = cohort_dir / "outputs"

        # Load analysis summary
        analysis_summary_path = output_dir / "main_survival_summary.csv"
        if analysis_summary_path.exists():
            analysis_summary = pd.read_csv(analysis_summary_path).iloc[0].to_dict()
        else:
            analysis_summary = {}
            logger.warning("main_survival_summary.csv not found")

        # Retrieve Causal Forest results if available
        cf_summary, cf_matched_df = workflow.get_causal_forest_results()
        
        # NEW: Retrieve multi-method matching results
        method_comparison_results = workflow._method_comparison_results
        selected_method = workflow._selected_method
        method_reasoning = workflow._method_selection_reasoning

        psm_results = {
            "analysis_summary": analysis_summary,
            "output_dir": str(output_dir),
        }

        # Store Causal Forest results in state
        if cf_summary is not None:
            logger.info("✅ Causal Forest results available - will be included in agent output")
            state["causal_forest_summary"] = cf_summary
            # Extract CATE values for frontend
            if cf_matched_df is not None and "cate_value" in cf_matched_df.columns:
                state["causal_forest_outcomes"] = cf_matched_df[["subject_id", "cate_value"]].to_dict("records")
        else:
            logger.warning("⚠️  Causal Forest results not available")
            state["causal_forest_summary"] = None
            state["causal_forest_outcomes"] = None
        
        # NEW: Store multi-method matching results in state
        if method_comparison_results is not None:
            logger.info(f"✅ Multi-method matching results available - selected: {selected_method}")
            state["method_comparison_results"] = method_comparison_results
            state["selected_method"] = selected_method
            state["method_selection_reasoning"] = method_reasoning
        else:
            state["method_comparison_results"] = None
            state["selected_method"] = None
            state["method_selection_reasoning"] = None

        state["psm_results"] = psm_results
        state["next_action"] = "interpret"

    else:
        logger.error("PSM + Survival Analysis failed")
        state["next_action"] = "error"

    return state


# ============================================================================
# Node 4: Interpret Results
# ============================================================================


def generate_structured_summary_node(state: StatisticianState) -> StatisticianState:
    """Node 4: Generate structured summary (no LLM required).

    Replaces LLM interpretation with structured statistical summary.
    Maintains 'interpretation' field for backward compatibility.

    Args:
        state: Current state with psm_results.

    Returns:
        Updated state with interpretation and structured_summary.
    """
    logger.info("=" * 70)
    logger.info("NODE 4: GENERATING STRUCTURED SUMMARY (No LLM)")
    logger.info("=" * 70)

    # Report progress
    progress_callback = state.get("progress_callback")
    if progress_callback:
        progress_callback("Generating statistical summary...")

    # Safely retrieve analysis summary with fallback
    analysis = state["psm_results"].get("analysis_summary", {})

    # If analysis_summary is empty, log error and return early
    if not analysis:
        logger.error("analysis_summary is missing or empty - cannot generate summary")
        state["interpretation"] = "# Statistical Analysis Failed\n\nAnalysis summary data is missing. Please check workflow execution logs."
        state["structured_summary"] = {"error": "analysis_summary missing"}
        return state

    # Helper function for safe formatting
    def fmt_num(val, decimals=3):
        """Format number safely, handling None/NaN."""
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "N/A"
        return f"{float(val):.{decimals}f}"

    def fmt_pct(val):
        """Format percentage safely."""
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "N/A"
        return f"{float(val) * 100:.1f}%"

    # Prepare Causal Forest section if available
    cf_summary = state.get("causal_forest_summary")
    if cf_summary:
        top_features = list(cf_summary.get("feature_importances", {}).items())[:5]
        features_str = "\n".join([f"  - {feat}: {imp:.3f}" for feat, imp in top_features])
        causal_forest_section = f"""
### Causal Forest Analysis (Heterogeneous Treatment Effects)
- **Average Treatment Effect (ATE)**: {fmt_num(cf_summary.get("ate", 0))}
- **Mean CATE**: {fmt_num(cf_summary.get("mean_cate", 0))} (±{fmt_num(cf_summary.get("cate_std", 0))})
- **CATE Range**: [{fmt_num(cf_summary.get("cate_range", [0, 0])[0])}, {fmt_num(cf_summary.get("cate_range", [0, 0])[1])}]
- **Positive Response Rate**: {fmt_pct(cf_summary.get("positive_response_rate", 0))} of patients benefit
- **Top 5 Effect Modifiers**:
{features_str}
"""
    else:
        causal_forest_section = ""

    # Markdown-formatted summary (for backward compatibility with frontend)
    interpretation = f"""# Statistical Analysis Summary

## PSM + Survival Analysis Results
- **Matched pairs**: {analysis.get('n_treatment', 'N/A')}
- **Hazard Ratio**: {fmt_num(analysis.get('cox_hr'))} (95% CI: {fmt_num(analysis.get('cox_ci_lower'))}-{fmt_num(analysis.get('cox_ci_upper'))})
- **P-value**: {fmt_num(analysis.get('cox_pvalue'), 4)}
- **Treatment mortality**: {fmt_pct(analysis.get('mortality_treatment', 0))}
- **Control mortality**: {fmt_pct(analysis.get('mortality_control', 0))}

{causal_forest_section}

## PSM Quality Metrics
- **Caliper**: {state['psm_params']['caliper_multiplier']} × SD
- **Matching strategy**: {state['psm_params']['matching_ratio']}
- **Variable selection**: {state['psm_params']['variable_selection_strategy']}
- **Pre-matching max SMD**: {fmt_num(state['baseline_imbalance']['max_smd'])}
- **Imbalanced variables**: {state['baseline_imbalance']['imbalanced_vars']}/{state['baseline_imbalance']['total_variables']}

---

*Note: This is a statistical summary only. Clinical interpretation and decision-making should be performed by domain experts with full knowledge of the clinical context.*
"""

    # Structured summary (for programmatic access)
    structured_summary = {
        "analysis_results": {
            "matched_pairs": analysis.get("n_treatment"),
            "hazard_ratio": analysis.get("cox_hr"),
            "ci_95_lower": analysis.get("cox_ci_lower"),
            "ci_95_upper": analysis.get("cox_ci_upper"),
            "p_value": analysis.get("cox_pvalue"),
            "mortality_treatment_pct": analysis.get("mortality_treatment", 0) * 100 if analysis.get("mortality_treatment") else None,
            "mortality_control_pct": analysis.get("mortality_control", 0) * 100 if analysis.get("mortality_control") else None,
        },
        "causal_forest": cf_summary if cf_summary else None,
        "psm_quality": {
            "caliper_multiplier": state["psm_params"]["caliper_multiplier"],
            "matching_ratio": state["psm_params"]["matching_ratio"],
            "variable_selection_strategy": state["psm_params"]["variable_selection_strategy"],
            "pre_matching_max_smd": state["baseline_imbalance"]["max_smd"],
            "imbalanced_vars": state["baseline_imbalance"]["imbalanced_vars"],
            "total_vars": state["baseline_imbalance"]["total_variables"],
        },
    }

    logger.info("=" * 70)
    logger.info("SUMMARY GENERATED")
    logger.info("=" * 70)
    logger.info(interpretation)

    state["interpretation"] = interpretation
    state["structured_summary"] = structured_summary

    # Save report (optional, for consistency with previous version)
    output_dir = Path(state["psm_results"]["output_dir"])
    report_path = output_dir / "statistician_report.md"

    report_content = f"""# Statistician Agent Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{interpretation}

---

## Cohort Details
- **Total patients**: {state['cohort_summary']['total_patients']:,}
- **Treatment**: {state['cohort_summary']['treatment_n']:,} ({state['cohort_summary']['treatment_pct']:.1f}%)
- **Control**: {state['cohort_summary']['control_n']:,} ({100-state['cohort_summary']['treatment_pct']:.1f}%)
- **Overall mortality**: {fmt_pct(state['cohort_summary'].get('mortality_overall'))}
"""

    with open(report_path, "w") as f:
        f.write(report_content)

    logger.info(f"Report saved to: {report_path}")

    return state


# ============================================================================
# Graph Construction
# ============================================================================


def create_statistician_graph() -> StateGraph:
    """Create compiled LangGraph workflow for statistician agent.

    Returns:
        Compiled StateGraph ready for invocation.

    Example:
        >>> graph = create_statistician_graph()
        >>> result = graph.invoke(initial_state)
    """
    workflow = StateGraph(StatisticianState)

    # Add nodes
    workflow.add_node("analyze_baseline", analyze_baseline_node)
    workflow.add_node("recommend_params", recommend_psm_params_node)
    workflow.add_node("execute_psm", execute_psm_workflow_node)
    workflow.add_node("generate_summary", generate_structured_summary_node)

    # Define edges (sequential flow)
    workflow.add_edge("analyze_baseline", "recommend_params")
    workflow.add_edge("recommend_params", "execute_psm")
    workflow.add_edge("execute_psm", "generate_summary")
    workflow.add_edge("generate_summary", END)

    # Set entry point
    workflow.set_entry_point("analyze_baseline")

    return workflow.compile()
