#!/usr/bin/env python3
"""
Statistician Agent - PSM Analysis Automation with LangGraph

This agent:
1. Analyzes baseline data characteristics
2. Recommends optimal PSM parameters
3. Executes PSM + Survival Analysis
4. Interprets results and generates report

Architecture:
- LangGraph for workflow orchestration
- OpenRouter (GPT-4o-mini) for intelligent decision making
- Statistical analysis tools for data processing

Usage:
    python scripts/agents/statistician.py \
        --cohort project/NCT03389555/cohorts/hydrocortisonenasucc/NCT03389555_hydrocortisonenasucc_v3.1_with_baseline.csv \
        --output-dir project/NCT03389555/cohorts/hydrocortisonenasucc/outputs
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import TypedDict, Annotated, Sequence
from datetime import datetime

import pandas as pd
import numpy as np
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LangChain & LangGraph imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from workflows.psm_survival_workflow import PSMSurvivalWorkflow


# ============================================================================
# Prompt Template Loader
# ============================================================================

def load_prompt_templates(prompts_file: str = None) -> dict:
    """Load prompt templates from YAML file"""
    if prompts_file is None:
        # Default path
        script_dir = Path(__file__).parent.parent.parent
        prompts_file = script_dir / "config" / "prompts" / "statistician_prompts.yaml"

    with open(prompts_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# Load prompts globally
PROMPTS = load_prompt_templates()


# ============================================================================
# State Definition
# ============================================================================

class StatisticianState(TypedDict):
    """Agent state for statistician workflow"""
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

    # Final report
    interpretation: str
    next_action: str


# ============================================================================
# Agent Nodes
# ============================================================================

def analyze_baseline_node(state: StatisticianState) -> StatisticianState:
    """
    Node 1: Analyze baseline data
    - Load cohort data
    - Calculate pre-matching SMD
    - Assess missingness
    - Summarize cohort characteristics
    """
    print("\n" + "=" * 70)
    print("NODE 1: BASELINE DATA ANALYSIS")
    print("=" * 70)

    cohort_path = state["cohort_path"]
    df = pd.read_csv(cohort_path)

    treatment = df[df['treatment_group'] == 1]
    control = df[df['treatment_group'] == 0]

    # Cohort summary
    cohort_summary = {
        "total_patients": len(df),
        "treatment_n": len(treatment),
        "control_n": len(control),
        "treatment_pct": len(treatment) / len(df) * 100,
        "mortality_overall": df['mortality'].mean() * 100 if 'mortality' in df.columns else None,
    }

    # Calculate pre-matching SMD for numeric variables
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    baseline_vars = [col for col in numeric_cols if col not in [
        'subject_id', 'hadm_id', 'stay_id', 'treatment_group', 'mortality'
    ]]

    smd_results = []
    for var in baseline_vars:
        if var in df.columns:
            t_data = treatment[var].dropna()
            c_data = control[var].dropna()

            if len(t_data) > 0 and len(c_data) > 0:
                t_mean = t_data.mean()
                t_std = t_data.std()
                c_mean = c_data.mean()
                c_std = c_data.std()

                pooled_std = np.sqrt((t_std**2 + c_std**2) / 2)
                smd = abs((t_mean - c_mean) / pooled_std) if pooled_std > 0 else 0

                smd_results.append({
                    'variable': var,
                    'smd': smd,
                    'treatment_mean': t_mean,
                    'control_mean': c_mean,
                    'imbalanced': smd > 0.1
                })

    smd_df = pd.DataFrame(smd_results).sort_values('smd', ascending=False)

    baseline_imbalance = {
        "total_variables": len(smd_df),
        "imbalanced_vars": len(smd_df[smd_df['smd'] > 0.1]),
        "max_smd": smd_df['smd'].max() if len(smd_df) > 0 else 0,
        "median_smd": smd_df['smd'].median() if len(smd_df) > 0 else 0,
        "top_imbalanced": smd_df.head(10).to_dict('records') if len(smd_df) > 0 else []
    }

    # Missingness analysis
    missing_pct = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    high_missing = missing_pct[missing_pct > 20]

    missingness_report = {
        "high_missing_count": len(high_missing),
        "high_missing_vars": high_missing.to_dict(),
        "median_missing_pct": missing_pct.median()
    }

    # Print summary
    print(f"\nCohort Summary:")
    print(f"  Total: {cohort_summary['total_patients']:,} patients")
    print(f"  Treatment: {cohort_summary['treatment_n']:,} ({cohort_summary['treatment_pct']:.1f}%)")
    print(f"  Control: {cohort_summary['control_n']:,} ({100-cohort_summary['treatment_pct']:.1f}%)")

    print(f"\nPre-matching Imbalance:")
    print(f"  Total variables: {baseline_imbalance['total_variables']}")
    print(f"  Imbalanced (SMD > 0.1): {baseline_imbalance['imbalanced_vars']}")
    print(f"  Max SMD: {baseline_imbalance['max_smd']:.3f}")
    print(f"  Median SMD: {baseline_imbalance['median_smd']:.3f}")

    print(f"\nMissingness:")
    print(f"  High missing (>20%): {missingness_report['high_missing_count']} variables")
    print(f"  Median missing %: {missingness_report['median_missing_pct']:.1f}%")

    state["cohort_summary"] = cohort_summary
    state["baseline_imbalance"] = baseline_imbalance
    state["missingness_report"] = missingness_report

    return state


def recommend_psm_params_node(state: StatisticianState) -> StatisticianState:
    """
    Node 2: LLM recommends PSM parameters
    - Analyze baseline imbalance and missingness
    - Recommend caliper size, matching ratio, variable selection strategy
    """
    print("\n" + "=" * 70)
    print("NODE 2: PSM PARAMETER RECOMMENDATION (GPT-4o-mini)")
    print("=" * 70)

    # Initialize OpenRouter-connected LLM
    llm = ChatOpenAI(
        model=PROMPTS['config']['model']['default'],
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=PROMPTS['config']['temperature']['parameter_recommendation'],
    )

    # Prepare context from YAML template
    template = PROMPTS['prompts']['parameter_recommendation']['template']

    context = template.format(
        total_patients=state['cohort_summary']['total_patients'],
        treatment_n=state['cohort_summary']['treatment_n'],
        treatment_pct=state['cohort_summary']['treatment_pct'],
        control_n=state['cohort_summary']['control_n'],
        control_pct=100 - state['cohort_summary']['treatment_pct'],
        total_variables=state['baseline_imbalance']['total_variables'],
        imbalanced_vars=state['baseline_imbalance']['imbalanced_vars'],
        max_smd=state['baseline_imbalance']['max_smd'],
        median_smd=state['baseline_imbalance']['median_smd'],
        top_imbalanced_json=json.dumps(state['baseline_imbalance']['top_imbalanced'][:5], indent=2),
        high_missing_count=state['missingness_report']['high_missing_count'],
        median_missing_pct=state['missingness_report']['median_missing_pct']
    )

    system_message = PROMPTS['system_messages']['parameter_recommendation']

    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=context)
    ]

    print("\n🤖 Querying GPT-4o-mini for PSM parameter recommendations...")

    response = llm.invoke(messages)
    response_text = response.content

    # Parse JSON response
    try:
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text

        psm_params = json.loads(json_text)

        print(f"\n✅ LLM Recommendations:")
        print(f"  Caliper: {psm_params['caliper_multiplier']} × SD")
        print(f"  Matching: {psm_params['matching_ratio']}")
        print(f"  Variable selection: {psm_params['variable_selection_strategy']}")
        print(f"  Exclude threshold: >{psm_params['exclude_threshold_pct']}% missing")
        print(f"\n  Rationale: {psm_params['rationale']}")

        state["psm_params"] = psm_params

        # Add to message history
        state["messages"].append(HumanMessage(content=context))
        state["messages"].append(AIMessage(content=response_text))

    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse LLM response as JSON: {e}")
        print(f"Raw response:\n{response_text}")

        # Fallback to default parameters
        psm_params = {
            "caliper_multiplier": 0.2,
            "matching_ratio": "1:1",
            "variable_selection_strategy": "exclude_high_missing",
            "exclude_threshold_pct": 20.0,
            "rationale": "Using default parameters due to JSON parsing error"
        }
        state["psm_params"] = psm_params

    return state


def execute_psm_workflow_node(state: StatisticianState) -> StatisticianState:
    """
    Node 3: Execute PSM + Survival Analysis
    - Run PSMSurvivalWorkflow with recommended parameters
    - Collect results
    """
    print("\n" + "=" * 70)
    print("NODE 3: EXECUTING PSM + SURVIVAL ANALYSIS")
    print("=" * 70)

    cohort_path = Path(state["cohort_path"])
    cohort_dir = cohort_path.parent

    # Initialize workflow
    workflow = PSMSurvivalWorkflow(
        project_dir=str(cohort_dir),
        data_csv=cohort_path.name,
        config_path=None  # Use default
    )

    # Execute workflow
    print(f"\n📊 Running PSM workflow with parameters:")
    print(f"  Caliper: {state['psm_params']['caliper_multiplier']} × SD")
    print(f"  Strategy: {state['psm_params']['variable_selection_strategy']}")

    result_code = workflow.run()

    if result_code == 0:
        print("\n✅ PSM + Survival Analysis completed successfully")

        # Load results
        output_dir = cohort_dir / "outputs"

        # Main survival summary
        main_summary_path = output_dir / "main_survival_summary.csv"
        if main_summary_path.exists():
            main_summary = pd.read_csv(main_summary_path).iloc[0].to_dict()
        else:
            main_summary = {}

        # Sensitivity survival summary
        sens_summary_path = output_dir / "sensitivity_survival_summary.csv"
        if sens_summary_path.exists():
            sens_summary = pd.read_csv(sens_summary_path).iloc[0].to_dict()
        else:
            sens_summary = {}

        psm_results = {
            "main_analysis": main_summary,
            "sensitivity_analysis": sens_summary,
            "output_dir": str(output_dir)
        }

        state["psm_results"] = psm_results
        state["next_action"] = "interpret"

    else:
        print("\n❌ PSM + Survival Analysis failed")
        state["next_action"] = "error"

    return state


def interpret_results_node(state: StatisticianState) -> StatisticianState:
    """
    Node 4: LLM interprets results and generates report
    - Analyze PSM quality (balance, matching rate)
    - Interpret survival analysis (HR, p-value, clinical significance)
    - Generate plain-language summary
    """
    print("\n" + "=" * 70)
    print("NODE 4: RESULTS INTERPRETATION (GPT-4o-mini)")
    print("=" * 70)

    # Initialize LLM
    llm = ChatOpenAI(
        model=PROMPTS['config']['model']['default'],
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=PROMPTS['config']['temperature']['results_interpretation'],
    )

    main = state["psm_results"]["main_analysis"]
    sens = state["psm_results"]["sensitivity_analysis"]

    # Prepare context from YAML template
    template = PROMPTS['prompts']['results_interpretation']['template']

    context = template.format(
        total_patients=state['cohort_summary']['total_patients'],
        treatment_n=state['cohort_summary']['treatment_n'],
        control_n=state['cohort_summary']['control_n'],
        caliper_multiplier=state['psm_params']['caliper_multiplier'],
        variable_selection_strategy=state['psm_params']['variable_selection_strategy'],
        main_n_treatment=main.get('n_treatment', 'N/A'),
        main_mortality_treatment=main.get('mortality_treatment', 0) * 100,
        main_mortality_control=main.get('mortality_control', 0) * 100,
        main_hr=main.get('cox_hr', 0),
        main_ci_lower=main.get('cox_ci_lower', 0),
        main_ci_upper=main.get('cox_ci_upper', 0),
        main_pvalue=main.get('cox_pvalue', 0),
        sens_n_treatment=sens.get('n_treatment', 'N/A'),
        sens_mortality_treatment=sens.get('mortality_treatment', 0) * 100,
        sens_mortality_control=sens.get('mortality_control', 0) * 100,
        sens_hr=sens.get('cox_hr', 0),
        sens_ci_lower=sens.get('cox_ci_lower', 0),
        sens_ci_upper=sens.get('cox_ci_upper', 0),
        sens_pvalue=sens.get('cox_pvalue', 0),
        treatment_n_original=state['cohort_summary']['treatment_n'],
        matching_rate=main.get('n_treatment', 0) / state['cohort_summary']['treatment_n'] * 100 if state['cohort_summary']['treatment_n'] > 0 else 0,
        pre_matching_max_smd=state['baseline_imbalance']['max_smd'],
        high_missing_count=state['missingness_report']['high_missing_count']
    )

    system_message = PROMPTS['system_messages']['results_interpretation']

    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=context)
    ]

    print("\n🤖 Querying GPT-4o-mini for results interpretation...")

    response = llm.invoke(messages)
    interpretation = response.content

    print("\n" + "=" * 70)
    print("INTERPRETATION")
    print("=" * 70)
    print(interpretation)

    state["interpretation"] = interpretation
    state["messages"].append(HumanMessage(content=context))
    state["messages"].append(AIMessage(content=interpretation))

    # Save report
    output_dir = Path(state["psm_results"]["output_dir"])
    report_path = output_dir / "statistician_report.md"

    report_content = f"""# Statistician Agent Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{interpretation}

---

## Analysis Details

### Cohort Summary
- Total patients: {state['cohort_summary']['total_patients']:,}
- Treatment: {state['cohort_summary']['treatment_n']:,} ({state['cohort_summary']['treatment_pct']:.1f}%)
- Control: {state['cohort_summary']['control_n']:,} ({100-state['cohort_summary']['treatment_pct']:.1f}%)

### Pre-matching Imbalance
- Imbalanced variables (SMD > 0.1): {state['baseline_imbalance']['imbalanced_vars']}/{state['baseline_imbalance']['total_variables']}
- Max SMD: {state['baseline_imbalance']['max_smd']:.3f}

### PSM Parameters
- Caliper: {state['psm_params']['caliper_multiplier']} × SD
- Matching: {state['psm_params']['matching_ratio']}
- Strategy: {state['psm_params']['variable_selection_strategy']}

### Results Summary
**Main Analysis:**
- HR: {main.get('cox_hr', 'N/A'):.3f} (95% CI: {main.get('cox_ci_lower', 'N/A'):.3f}-{main.get('cox_ci_upper', 'N/A'):.3f})
- P-value: {main.get('cox_pvalue', 'N/A'):.4f}

**Sensitivity Analysis:**
- HR: {sens.get('cox_hr', 'N/A'):.3f} (95% CI: {sens.get('cox_ci_lower', 'N/A'):.3f}-{sens.get('cox_ci_upper', 'N/A'):.3f})
- P-value: {sens.get('cox_pvalue', 'N/A'):.4f}
"""

    with open(report_path, 'w') as f:
        f.write(report_content)

    print(f"\n📄 Report saved to: {report_path}")

    return state


# ============================================================================
# Graph Construction
# ============================================================================

def create_statistician_graph():
    """Create LangGraph workflow for statistician agent"""

    workflow = StateGraph(StatisticianState)

    # Add nodes
    workflow.add_node("analyze_baseline", analyze_baseline_node)
    workflow.add_node("recommend_params", recommend_psm_params_node)
    workflow.add_node("execute_psm", execute_psm_workflow_node)
    workflow.add_node("interpret_results", interpret_results_node)

    # Define edges
    workflow.add_edge("analyze_baseline", "recommend_params")
    workflow.add_edge("recommend_params", "execute_psm")
    workflow.add_edge("execute_psm", "interpret_results")
    workflow.add_edge("interpret_results", END)

    # Set entry point
    workflow.set_entry_point("analyze_baseline")

    return workflow.compile()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Statistician Agent - Automated PSM Analysis with LangGraph',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--cohort',
        required=True,
        help='Path to cohort CSV with baseline characteristics'
    )

    parser.add_argument(
        '--output-dir',
        help='Output directory (optional, defaults to cohort parent dir / outputs)'
    )

    args = parser.parse_args()

    cohort_path = Path(args.cohort)

    if not cohort_path.exists():
        print(f"❌ Error: Cohort file not found: {cohort_path}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else cohort_path.parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check OpenRouter API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ Error: OPENROUTER_API_KEY environment variable not set")
        print("Set it with: export OPENROUTER_API_KEY='your-key-here'")
        return 1

    print("=" * 80)
    print("STATISTICIAN AGENT - Automated PSM Analysis")
    print("=" * 80)
    print(f"\nCohort: {cohort_path}")
    print(f"Output: {output_dir}")
    print(f"LLM: GPT-4o-mini via OpenRouter")
    print()

    # Initialize state
    initial_state = {
        "messages": [],
        "cohort_path": str(cohort_path),
        "output_dir": str(output_dir),
        "cohort_summary": {},
        "baseline_imbalance": {},
        "missingness_report": {},
        "psm_params": {},
        "psm_results": {},
        "survival_results": {},
        "interpretation": "",
        "next_action": ""
    }

    # Create and run graph
    graph = create_statistician_graph()

    try:
        final_state = graph.invoke(initial_state)

        print("\n" + "=" * 80)
        print("✅ STATISTICIAN AGENT COMPLETED")
        print("=" * 80)
        print(f"\nGenerated files in: {output_dir}")
        print("  📄 statistician_report.md - Full interpretation")
        print("  📊 matched_data_main.csv")
        print("  📈 main_analysis_cumulative_mortality.png")
        print("  📋 baseline_table_main_JAMA.md")
        print("  ... and more")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
