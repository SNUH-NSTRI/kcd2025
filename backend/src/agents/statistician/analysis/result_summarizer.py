"""
Result Summarizer Module

Generates structured summaries of statistical analysis results using LLM.
Creates Question, Conclusion, and PICO (Population, Intervention, Findings) format
for easy interpretation of complex statistical outputs.
"""

import os
import logging
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


def generate_analysis_summary(
    nct_id: str,
    medication: str,
    cohort_summary: Dict[str, Any],
    main_analysis: Dict[str, Any],
    sensitivity_analysis: Optional[Dict[str, Any]] = None,
    openrouter_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate structured summary of analysis results using LLM.

    Args:
        nct_id: Clinical trial NCT ID
        medication: Medication being studied
        cohort_summary: Dictionary with total_patients, treatment_n, control_n, etc.
        main_analysis: Main analysis results (matched_pairs, hazard_ratio, p_value, etc.)
        sensitivity_analysis: Optional sensitivity analysis results
        openrouter_api_key: OpenRouter API key (uses env var if None)

    Returns:
        Dictionary with keys: question, conclusion, population, intervention, findings
    """
    api_key = openrouter_api_key or os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        logger.warning("No OpenRouter API key provided, returning default summary")
        return _generate_default_summary(
            nct_id, medication, cohort_summary, main_analysis
        )

    # Prepare detailed prompt
    prompt = _build_summary_prompt(
        nct_id, medication, cohort_summary, main_analysis, sensitivity_analysis
    )

    try:
        # Call OpenRouter API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a biostatistician expert. Summarize statistical analysis results "
                            "in a structured format following clinical trial reporting standards."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            },
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"OpenRouter API failed: {response.status_code} - {response.text}")
            return _generate_default_summary(
                nct_id, medication, cohort_summary, main_analysis
            )

        result = response.json()
        content = result['choices'][0]['message']['content']

        # Parse the LLM response
        summary = _parse_llm_response(content)

        logger.info("Successfully generated LLM-based analysis summary")
        return summary

    except Exception as e:
        logger.exception(f"Failed to generate LLM summary: {e}")
        return _generate_default_summary(
            nct_id, medication, cohort_summary, main_analysis
        )


def _build_summary_prompt(
    nct_id: str,
    medication: str,
    cohort_summary: Dict[str, Any],
    main_analysis: Dict[str, Any],
    sensitivity_analysis: Optional[Dict[str, Any]] = None
) -> str:
    """Build detailed prompt for LLM summarization."""

    lines = []
    lines.append(f"# Statistical Analysis Results Summary")
    lines.append(f"")
    lines.append(f"Study: {nct_id}")
    lines.append(f"Intervention: {medication}")
    lines.append(f"")
    lines.append(f"## Cohort Summary")
    lines.append(f"- Total patients: {cohort_summary.get('total_patients', 'N/A')}")
    lines.append(f"- Treatment group: {cohort_summary.get('treatment_n', 'N/A')} ({cohort_summary.get('treatment_pct', 'N/A'):.1f}%)")
    lines.append(f"- Control group: {cohort_summary.get('control_n', 'N/A')}")
    lines.append(f"")
    lines.append(f"## Main Analysis Results")
    lines.append(f"- Matched pairs: {main_analysis.get('matched_pairs', 'N/A')}")
    lines.append(f"- Cox Hazard Ratio: {main_analysis.get('hazard_ratio', 'N/A'):.3f}")
    lines.append(f"- 95% CI: [{main_analysis.get('ci_95_lower', 'N/A'):.3f} - {main_analysis.get('ci_95_upper', 'N/A'):.3f}]")
    lines.append(f"- P-value: {main_analysis.get('p_value', 'N/A'):.4f}")
    lines.append(f"- Treatment mortality: {main_analysis.get('mortality_treatment_pct', 'N/A'):.1f}%")
    lines.append(f"- Control mortality: {main_analysis.get('mortality_control_pct', 'N/A'):.1f}%")
    lines.append(f"")

    if sensitivity_analysis:
        lines.append(f"## Sensitivity Analysis")
        lines.append(f"- Matched pairs: {sensitivity_analysis.get('matched_pairs', 'N/A')}")
        lines.append(f"- Cox Hazard Ratio: {sensitivity_analysis.get('hazard_ratio', 'N/A'):.3f}")
        lines.append(f"- P-value: {sensitivity_analysis.get('p_value', 'N/A'):.4f}")
        lines.append(f"")

    lines.append(f"## Task")
    lines.append(f"Generate a structured summary with the following sections:")
    lines.append(f"")
    lines.append(f"1. **QUESTION**: State the research question in one clear sentence")
    lines.append(f"   Format: 'What is the effect of [intervention] on [outcome] in [population]?'")
    lines.append(f"")
    lines.append(f"2. **CONCLUSION**: State the main finding in one clear sentence")
    lines.append(f"   - If p < 0.05: State the significant effect")
    lines.append(f"   - If p >= 0.05: State 'No significant difference in [outcome] was observed between treatment and control groups (p=[value])'")
    lines.append(f"")
    lines.append(f"3. **POPULATION**: Describe the study population")
    lines.append(f"   - Total number of patients")
    lines.append(f"   - Treatment group (n, %)")
    lines.append(f"   - Control group (n)")
    lines.append(f"   - Brief patient description (e.g., 'Adults with septic shock requiring vasopressors')")
    lines.append(f"")
    lines.append(f"4. **INTERVENTION**: Describe treatment and control")
    lines.append(f"   - Treatment group: What they received and outcome")
    lines.append(f"   - Control group: What they received and outcome")
    lines.append(f"   - Primary outcome definition")
    lines.append(f"")
    lines.append(f"5. **FINDINGS**: Statistical results")
    lines.append(f"   - Cox Hazard Ratio with 95% CI")
    lines.append(f"   - P-value")
    lines.append(f"   - Absolute risk difference in percentage points")
    lines.append(f"   - Hazard increase/decrease percentage")
    lines.append(f"   - Statistical significance conclusion")
    lines.append(f"")
    lines.append(f"Respond in the following exact JSON format:")
    lines.append(f'{{')
    lines.append(f'  "question": "...",')
    lines.append(f'  "conclusion": "...",')
    lines.append(f'  "population": {{')
    lines.append(f'    "total_patients": 12345,')
    lines.append(f'    "treatment_n": 623,')
    lines.append(f'    "control_n": 11722,')
    lines.append(f'    "description": "..."')
    lines.append(f'  }},')
    lines.append(f'  "intervention": {{')
    lines.append(f'    "treatment_group": "...",')
    lines.append(f'    "control_group": "...",')
    lines.append(f'    "primary_outcome": "..."')
    lines.append(f'  }},')
    lines.append(f'  "findings": {{')
    lines.append(f'    "cox_hazard_ratio": 1.040,')
    lines.append(f'    "ci_95": "0.899 - 1.202",')
    lines.append(f'    "p_value": 0.5971,')
    lines.append(f'    "absolute_risk_difference": "+2.1 percentage points",')
    lines.append(f'    "hazard_change": "+4.0%",')
    lines.append(f'    "significance": "Not statistically significant"')
    lines.append(f'  }}')
    lines.append(f'}}')

    return "\n".join(lines)


def _parse_llm_response(content: str) -> Dict[str, Any]:
    """Parse LLM response into structured summary."""
    import json

    # Try to extract JSON from the response
    try:
        # Find JSON block in the response
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1

        if start_idx >= 0 and end_idx > start_idx:
            json_str = content[start_idx:end_idx]
            return json.loads(json_str)
        else:
            logger.warning("No JSON found in LLM response, returning empty summary")
            return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return {}


def _generate_default_summary(
    nct_id: str,
    medication: str,
    cohort_summary: Dict[str, Any],
    main_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a default summary when LLM is unavailable."""

    hr = main_analysis.get('hazard_ratio', 1.0)
    p_value = main_analysis.get('p_value', 1.0)
    ci_lower = main_analysis.get('ci_95_lower', 0.0)
    ci_upper = main_analysis.get('ci_95_upper', 2.0)

    mortality_tx = main_analysis.get('mortality_treatment_pct', 0.0)
    mortality_ctrl = main_analysis.get('mortality_control_pct', 0.0)
    abs_diff = mortality_tx - mortality_ctrl

    # Determine significance
    is_significant = p_value < 0.05
    significance_text = "statistically significant" if is_significant else "Not statistically significant"

    # Build conclusion
    if is_significant:
        if hr > 1:
            conclusion = f"Significant increase in mortality was observed with {medication} (p={p_value:.4f})."
        else:
            conclusion = f"Significant decrease in mortality was observed with {medication} (p={p_value:.4f})."
    else:
        conclusion = f"No significant difference in mortality was observed between treatment and control groups (p={p_value:.4f})."

    return {
        "question": f"What is the effect of {medication} on 28-day mortality in septic shock patients?",
        "conclusion": conclusion,
        "population": {
            "total_patients": cohort_summary.get('total_patients', 0),
            "treatment_n": cohort_summary.get('treatment_n', 0),
            "control_n": cohort_summary.get('control_n', 0),
            "description": "Adults with septic shock requiring vasopressors"
        },
        "intervention": {
            "treatment_group": f"Received {medication}",
            "control_group": "Standard care",
            "primary_outcome": "28-day all-cause mortality"
        },
        "findings": {
            "cox_hazard_ratio": hr,
            "ci_95": f"{ci_lower:.3f} - {ci_upper:.3f}",
            "p_value": p_value,
            "absolute_risk_difference": f"{abs_diff:+.1f} percentage points",
            "hazard_change": f"{(hr - 1) * 100:+.1f}%",
            "significance": significance_text
        }
    }
