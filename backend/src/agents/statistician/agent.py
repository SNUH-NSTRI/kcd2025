"""Statistician Agent - BaseAgent implementation.

This module provides the StatisticianAgent class that implements the BaseAgent
interface for PSM (Propensity Score Matching) + Survival Analysis automation.

The agent orchestrates a 4-node LangGraph workflow:
    1. Analyze baseline data characteristics
    2. Use default PSM parameters (no LLM)
    3. Execute PSM + Survival Analysis
    4. Generate structured summary (no LLM)

Following vooster-docs/clean-code.md:
- Single Responsibility: Agent only handles orchestration
- Dependency Injection: All external dependencies passed in
- Interface Segregation: Implements only BaseAgent methods
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from agents.base import AgentResult, AgentStatus, BaseAgent
from rwe_api.config import settings  # Centralized config
from agents.statistician.graph import (
    StatisticianState,
    create_statistician_graph,
    load_prompt_templates,
)
from agents.statistician.utils import (
    construct_cohort_path,
    construct_output_dir,
    validate_medication,
    validate_nct_id,
)

logger = logging.getLogger(__name__)


# Import register_agent at runtime to avoid circular import
def _register_on_import():
    """Register this agent when module is imported."""
    from agents import register_agent
    return register_agent


@_register_on_import()
class StatisticianAgent(BaseAgent):
    """Statistician Agent for automated PSM analysis.

    This agent uses LangGraph to orchestrate a complex statistical analysis
    workflow with LLM-powered decision making at key steps.

    Attributes:
        name: Agent identifier ("statistician")
        description: Human-readable description of agent capabilities
    """

    def __init__(self):
        """Initialize Statistician Agent."""
        self.name = "statistician"
        self.version = "0.1.0"
        self.description = (
            "Automated PSM (Propensity Score Matching) + Survival Analysis. "
            "Analyzes baseline data, executes analysis with default parameters, "
            "and generates structured statistical summaries."
        )

    async def validate_inputs(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate input parameters before execution.

        Required kwargs:
            nct_id: NCT ID (format: NCT########)
            medication: Medication name (non-empty string)
            openrouter_api_key: OpenRouter API key (optional if in env)
            workspace_root: Workspace root directory (optional, defaults to CWD)

        Returns:
            (True, None) if valid
            (False, error_message) if invalid

        Following TDD principles from vooster-docs/tdd.md:
        - Test behavior (validation), not implementation
        - Fast and independent checks
        """
        # Required parameters
        nct_id = kwargs.get("nct_id")
        medication = kwargs.get("medication")

        if not nct_id:
            return False, "nct_id is required"

        if not medication:
            return False, "medication is required"

        # Validate NCT ID format
        is_valid, error = validate_nct_id(nct_id)
        if not is_valid:
            return False, f"Invalid NCT ID: {error}"

        # Validate medication name
        is_valid, error = validate_medication(medication)
        if not is_valid:
            return False, f"Invalid medication: {error}"

        # Validate cohort file exists
        workspace_root = kwargs.get("workspace_root")
        try:
            cohort_path = construct_cohort_path(nct_id, medication, workspace_root)
            logger.info(f"Cohort file validated: {cohort_path}")
        except FileNotFoundError as e:
            return False, str(e)
        except ValueError as e:
            return False, str(e)

        # Validate OpenRouter API key
        openrouter_api_key = kwargs.get("openrouter_api_key") or settings.OPENROUTER_API_KEY
        if not openrouter_api_key:
            return False, (
                "OPENROUTER_API_KEY not provided. "
                "Set environment variable or pass as parameter."
            )

        return True, None

    async def run(self, **kwargs) -> AgentResult:
        """Execute the agent's main logic.

        Required kwargs:
            nct_id: NCT ID
            medication: Medication name
            openrouter_api_key: OpenRouter API key (optional if in env)
            workspace_root: Workspace root (optional)
            prompts_file: Path to prompts YAML (optional)
            progress_callback: Optional callback to update progress (optional)

        Returns:
            AgentResult with success status, output data, and error if any.

        Raises:
            Should not raise exceptions - errors captured in AgentResult.
        """
        logger.info("=" * 80)
        logger.info("STATISTICIAN AGENT - Starting execution")
        logger.info("=" * 80)

        try:
            # Extract parameters
            nct_id = kwargs["nct_id"]
            medication = kwargs["medication"]
            workspace_root = kwargs.get("workspace_root")
            prompts_file = kwargs.get("prompts_file")
            progress_callback = kwargs.get("progress_callback")

            # Get API key (from kwargs, or settings which ALWAYS loads .env)
            openrouter_api_key = kwargs.get("openrouter_api_key") or settings.OPENROUTER_API_KEY

            # Construct paths (already validated in validate_inputs)
            cohort_path = construct_cohort_path(nct_id, medication, workspace_root)
            output_dir = construct_output_dir(nct_id, medication, workspace_root)

            # Calculate relative path for API response (decouple from backend filesystem)
            try:
                relative_output_dir = Path(output_dir).relative_to(settings.WORKSPACE_ROOT)
            except ValueError:
                # Fallback if output_dir is not within WORKSPACE_ROOT
                logger.warning("Could not create relative path for output_dir. Using full path.")
                relative_output_dir = Path(output_dir)

            logger.info(f"NCT ID: {nct_id}")
            logger.info(f"Medication: {medication}")
            logger.info(f"Cohort: {cohort_path}")
            logger.info(f"Output (absolute): {output_dir}")
            logger.info(f"Output (relative): {relative_output_dir}")

            # Load prompts
            prompts = load_prompt_templates(
                Path(prompts_file) if prompts_file else None
            )
            logger.info(f"Loaded prompts: {prompts.get('config', {}).get('version', 'unknown')}")

            # Initialize state
            initial_state: StatisticianState = {
                "messages": [],
                "cohort_path": str(cohort_path),
                "output_dir": str(output_dir),
                "cohort_summary": {},
                "baseline_imbalance": {},
                "missingness_report": {},
                "psm_params": {},
                "psm_results": {},
                "survival_results": {},
                "causal_forest_summary": None,
                "causal_forest_outcomes": None,
                "interpretation": "",
                "next_action": "",
                "prompts": prompts,
                "openrouter_api_key": openrouter_api_key,
                "progress_callback": progress_callback,
            }

            # Create and run graph
            graph = create_statistician_graph()
            logger.info("Executing LangGraph workflow...")

            # CRITICAL FIX: Run blocking graph.invoke in separate thread
            # to prevent blocking FastAPI's event loop, allowing progress polling
            final_state = await asyncio.to_thread(graph.invoke, initial_state)

            logger.info("=" * 80)
            logger.info("STATISTICIAN AGENT - Completed successfully")
            logger.info("=" * 80)

            # Collect multi-method matching results from final state
            method_comparisons = None
            selected_method = None
            method_reasoning = None
            
            if "method_comparison_results" in final_state:
                method_comps = final_state["method_comparison_results"]
                method_comparisons = [
                    {
                        "method_name": method_name,
                        "n_matched": result["n_matched"],
                        "mean_smd": result["mean_smd"],
                        "balanced_pct": result["balanced_pct"],
                        "smd_details": result["smd_dict"]
                    }
                    for method_name, result in method_comps.items()
                ]
            
            if "selected_method" in final_state:
                selected_method = final_state["selected_method"]
            
            if "method_selection_reasoning" in final_state:
                method_reasoning = final_state["method_selection_reasoning"]

            # Generate LLM-based summary
            llm_summary = {}
            try:
                from agents.statistician.analysis.result_summarizer import generate_analysis_summary

                # Extract structured summary from PSM results
                structured_summary = final_state.get("psm_results", {}).get("structured_summary")
                if structured_summary:
                    llm_summary = generate_analysis_summary(
                        nct_id=nct_id,
                        medication=medication,
                        cohort_summary=final_state["cohort_summary"],
                        main_analysis=structured_summary.get("main_analysis", {}),
                        sensitivity_analysis=structured_summary.get("sensitivity_analysis"),
                        openrouter_api_key=openrouter_api_key
                    )
                    logger.info("Generated LLM-based analysis summary")
            except Exception as e:
                logger.exception(f"Failed to generate LLM summary: {e}")

            # Return success result
            return AgentResult(
                status=AgentStatus.COMPLETED,
                agent_name=self.name,
                output_dir=str(relative_output_dir),  # CRITICAL FIX: Use relative path for API
                result_data={
                    "cohort_summary": final_state["cohort_summary"],
                    "baseline_imbalance": final_state["baseline_imbalance"],
                    "missingness_report": final_state["missingness_report"],
                    "psm_params": final_state["psm_params"],
                    "psm_results": final_state["psm_results"],
                    "interpretation": final_state["interpretation"],
                    "outcomes": final_state.get("causal_forest_outcomes"),  # CATE values for frontend
                    "method_comparisons": method_comparisons,  # NEW: Multi-method comparison
                    "selected_method": selected_method,  # NEW: Best method selected by LLM
                    "method_reasoning": method_reasoning,  # NEW: LLM reasoning
                    "llm_summary": llm_summary,  # NEW: LLM-generated summary (Question, Conclusion, PICO)
                    "visualizations": {
                        "baseline_table_main": "baseline_table_main_JAMA.md",
                        "baseline_table_sensitivity": "baseline_table_sensitivity_JAMA.md",
                        "love_plot_main": "main_analysis_smd_plot.png",
                        "love_plot_sensitivity": "sensitivity_analysis_smd_plot.png",
                        "kaplan_meier_main": "main_analysis_cumulative_mortality.png",
                        "kaplan_meier_sensitivity": "sensitivity_analysis_cumulative_mortality.png",
                    },
                },
                metadata={
                    "nct_id": nct_id,
                    "medication": medication,
                    "cohort_path": str(cohort_path),
                    "llm_model": prompts.get("config", {})
                    .get("model", {})
                    .get("default", "unknown"),
                    "summary": {
                        "causal_forest": final_state.get("causal_forest_summary"),
                    } if final_state.get("causal_forest_summary") else {},
                },
                error=None,
            )

        except Exception as e:
            logger.exception("Statistician Agent failed with exception")
            return AgentResult(
                status=AgentStatus.FAILED,
                agent_name=self.name,
                output_dir=None,
                result_data={},
                metadata={
                    "nct_id": kwargs.get("nct_id"),
                    "medication": kwargs.get("medication"),
                },
                error=str(e),
            )

    def get_output_files(self, output_dir: str) -> list[Path]:
        """Get list of files generated by this agent.

        Args:
            output_dir: Output directory path (e.g., project/NCT03389555/cohorts/hydrocortisonenasucc/outputs)

        Returns:
            List of Path objects for generated files.

        Note:
            This list matches the PSMSurvivalWorkflow output specification.
        """
        output_path = Path(output_dir)

        expected_files = [
            # Statistician report
            "statistician_report.md",
            # Main analysis
            "matched_data_main.csv",
            "baseline_table_main_JAMA.md",
            "main_analysis_smd_plot.png",  # Love Plot (Standardized Mean Difference)
            "main_analysis_cumulative_mortality.png",  # Kaplan-Meier Plot
            "main_survival_summary.csv",
            # Sensitivity analysis
            "matched_data_sensitivity.csv",
            "baseline_table_sensitivity_JAMA.md",
            "sensitivity_analysis_smd_plot.png",  # Love Plot (Standardized Mean Difference)
            "sensitivity_analysis_cumulative_mortality.png",  # Kaplan-Meier Plot
            "sensitivity_survival_summary.csv",
            # Additional outputs (may vary)
            "balance_assessment_main.csv",
            "balance_assessment_sensitivity.csv",
        ]

        return [output_path / filename for filename in expected_files if (output_path / filename).exists()]
