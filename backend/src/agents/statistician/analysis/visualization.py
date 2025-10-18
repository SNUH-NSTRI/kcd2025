"""
Visualization Module for PSM + Survival Analysis

Generates publication-ready plots:
- SMD plot (before/after matching)
- Kaplan-Meier curves with risk table
"""

import matplotlib
# CRITICAL: Use non-interactive backend for thread safety
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
from lifelines import KaplanMeierFitter


def generate_smd_plot(
    matched_df: pd.DataFrame,
    variables: list,
    output_path: Path,
    analysis_type: str = "main"
) -> Path:
    """
    Generate Love Plot (SMD scatter plot) showing covariate balance after matching.

    Following best practices from clinical research:
    - Displays ALL pre-treatment covariates from PSM model
    - Uses scatter points (standard in publications)
    - Color-coded by balance quality (green < 0.1, orange < 0.2, red >= 0.2)

    Args:
        matched_df: Matched cohort data
        variables: List of variable names to plot
        output_path: Path to save plot
        analysis_type: "main" or "sensitivity"

    Returns:
        Path to saved plot
    """
    treat_col = 'treatment_group' if 'treatment_group' in matched_df.columns else 'treat'
    treatment = matched_df[matched_df[treat_col] == 1]
    control = matched_df[matched_df[treat_col] == 0]

    # ⭐ CRITICAL: Exclusion list updated per Zen's guidance
    # ONLY exclude: IDs, treatment indicator, outcomes, post-treatment measures
    # DO NOT exclude: gender, race (these are essential confounders!)
    exclude_from_plot = {
        'subject_id', 'hadm_id', 'stay_id',  # Identifiers
        'treatment_group', 'treat',  # Treatment indicator
        'mortality', 'death_28d', 'survival_time_28d', 'outcome_days',  # Outcomes
        'icu_outtime', 'date_of_death', 'dod',  # Post-treatment timestamps
        'days_to_death', 'los',  # Post-treatment durations
    }

    smd_data = []

    for var in variables:
        if var in matched_df.columns and var not in exclude_from_plot:
            try:
                t_mean = treatment[var].mean()
                t_std = treatment[var].std()
                c_mean = control[var].mean()
                c_std = control[var].std()

                pooled_std = np.sqrt((t_std**2 + c_std**2) / 2)
                smd = (t_mean - c_mean) / pooled_std if pooled_std > 0 else 0

                smd_data.append({'variable': var, 'smd': smd})
            except:
                pass

    smd_df = pd.DataFrame(smd_data)
    # Sort by absolute SMD (descending) - worst imbalances at top
    smd_df['abs_smd'] = smd_df['smd'].abs()
    smd_df = smd_df.sort_values('abs_smd', ascending=True)  # Bottom to top

    # Create plot with scatter points (standard Love Plot style)
    fig, ax = plt.subplots(figsize=(10, max(6, len(smd_df) * 0.3)))

    # Color coding based on absolute SMD
    colors = ['#27AE60' if abs(x) < 0.1 else '#F39C12' if abs(x) < 0.2 else '#E74C3C'
              for x in smd_df['smd']]

    # ⭐ USER REQUEST: Use scatter points instead of bars
    y_positions = range(len(smd_df))
    ax.scatter(smd_df['smd'], y_positions, s=120, c=colors, alpha=0.8,
               edgecolors='black', linewidths=0.5, zorder=3)

    # Reference lines
    ax.axvline(-0.1, color='gray', linestyle='--', linewidth=1, alpha=0.5, zorder=1)
    ax.axvline(0.1, color='gray', linestyle='--', linewidth=1, alpha=0.5, zorder=1)
    ax.axvline(0, color='black', linestyle='-', linewidth=1.5, zorder=2)

    # Styling
    ax.set_yticks(y_positions)
    ax.set_yticklabels(smd_df['variable'], fontsize=9)
    ax.set_xlabel('Standardized Mean Difference (SMD)', fontsize=12, weight='bold')
    ax.set_title(f'Love Plot: Covariate Balance After Matching - {analysis_type.capitalize()}',
                 fontsize=14, weight='bold')
    ax.grid(axis='x', alpha=0.3, linestyle=':', zorder=0)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#27AE60', label='Good balance (|SMD| < 0.1)'),
        Patch(facecolor='#F39C12', label='Acceptable (0.1 ≤ |SMD| < 0.2)'),
        Patch(facecolor='#E74C3C', label='Poor balance (|SMD| ≥ 0.2)')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9, frameon=True)

    # Set x-axis limits for better visualization
    max_abs_smd = max(smd_df['smd'].abs().max(), 0.25)  # At least show to 0.25
    ax.set_xlim(-max_abs_smd * 1.1, max_abs_smd * 1.1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path


def generate_love_plot_before_after(
    original_df: pd.DataFrame,
    matched_df: pd.DataFrame,
    variables: list,
    output_path: Path,
    analysis_type: str = "main"
) -> Path:
    """
    Generate Love Plot showing SMD before AND after matching (like the image).

    This is the academically rigorous visualization that shows:
    - Before matching (triangles): Demonstrates the problem
    - After matching (circles): Demonstrates the solution

    Args:
        original_df: Original (pre-matching) cohort
        matched_df: Matched cohort data
        variables: List of variable names to plot
        output_path: Path to save plot
        analysis_type: "main" or "sensitivity"

    Returns:
        Path to saved plot
    """
    treat_col = 'treatment_group' if 'treatment_group' in matched_df.columns else 'treat'

    # Exclude non-baseline variables
    exclude_from_plot = {
        'subject_id', 'hadm_id', 'stay_id',
        'treatment_group', 'treat',
        'mortality', 'death_28d', 'survival_time_28d', 'outcome_days',
        'icu_outtime', 'date_of_death', 'dod',
        'days_to_death', 'los',
    }

    smd_data = []

    for var in variables:
        if var in matched_df.columns and var not in exclude_from_plot:
            try:
                # Skip non-numeric variables
                if not pd.api.types.is_numeric_dtype(matched_df[var]):
                    continue

                # BEFORE matching SMD
                orig_treat = original_df[original_df[treat_col] == 1][var]
                orig_ctrl = original_df[original_df[treat_col] == 0][var]

                t_mean_before = orig_treat.mean()
                t_std_before = orig_treat.std()
                c_mean_before = orig_ctrl.mean()
                c_std_before = orig_ctrl.std()

                pooled_std_before = np.sqrt((t_std_before**2 + c_std_before**2) / 2)
                smd_before = (t_mean_before - c_mean_before) / pooled_std_before if pooled_std_before > 0 else 0

                # AFTER matching SMD
                match_treat = matched_df[matched_df[treat_col] == 1][var]
                match_ctrl = matched_df[matched_df[treat_col] == 0][var]

                t_mean_after = match_treat.mean()
                t_std_after = match_treat.std()
                c_mean_after = match_ctrl.mean()
                c_std_after = match_ctrl.std()

                pooled_std_after = np.sqrt((t_std_after**2 + c_std_after**2) / 2)
                smd_after = (t_mean_after - c_mean_after) / pooled_std_after if pooled_std_after > 0 else 0

                smd_data.append({
                    'variable': var,
                    'smd_before': smd_before,
                    'smd_after': smd_after,
                    'improved': abs(smd_after) < abs(smd_before)
                })
            except Exception as e:
                print(f"Warning: Could not calculate SMD for {var}: {e}")
                pass

    if not smd_data:
        print(f"Warning: No valid SMD data for plotting")
        return output_path

    smd_df = pd.DataFrame(smd_data)

    # Sort by absolute BEFORE SMD (show worst imbalances at top)
    smd_df['abs_smd_before'] = smd_df['smd_before'].abs()
    smd_df = smd_df.sort_values('abs_smd_before', ascending=True)  # Bottom to top

    # Create plot (like the reference image)
    fig, ax = plt.subplots(figsize=(12, max(8, len(smd_df) * 0.4)))

    y_positions = range(len(smd_df))

    # Plot BEFORE matching (triangles - cyan/teal)
    ax.scatter(smd_df['smd_before'], y_positions,
               s=150, marker='^', c='#17A589', alpha=0.7,
               edgecolors='black', linewidths=0.5, zorder=3,
               label='Before matching')

    # Plot AFTER matching (circles - coral/salmon)
    ax.scatter(smd_df['smd_after'], y_positions,
               s=150, marker='o', c='#E74C3C', alpha=0.7,
               edgecolors='black', linewidths=0.5, zorder=3,
               label='After matching')

    # Reference lines at ±10% (good balance threshold)
    ax.axvline(-0.1, color='gray', linestyle='--', linewidth=1.5, alpha=0.6, zorder=1)
    ax.axvline(0.1, color='gray', linestyle='--', linewidth=1.5, alpha=0.6, zorder=1)
    ax.axvline(0, color='black', linestyle='-', linewidth=2, zorder=2)

    # Styling
    ax.set_yticks(y_positions)
    ax.set_yticklabels(smd_df['variable'], fontsize=10)
    ax.set_xlabel('Standardized Mean Difference (%)', fontsize=13, weight='bold')
    ax.set_title(f'Covariate Balance: Before vs After Propensity Score Matching\n({analysis_type.capitalize()} Analysis)',
                 fontsize=14, weight='bold', pad=20)
    ax.grid(axis='x', alpha=0.3, linestyle=':', zorder=0)

    # Legend
    ax.legend(loc='lower right', fontsize=11, frameon=True,
              shadow=True, fancybox=True)

    # X-axis: Show as percentage
    max_abs_smd = max(smd_df['smd_before'].abs().max(),
                      smd_df['smd_after'].abs().max(), 0.3)
    ax.set_xlim(-max_abs_smd * 1.15, max_abs_smd * 1.15)

    # Add text annotation showing balance improvement
    n_improved = smd_df['improved'].sum()
    n_total = len(smd_df)
    ax.text(0.98, 0.02,
            f'{n_improved}/{n_total} variables improved\nGood balance: |SMD| < 0.1',
            transform=ax.transAxes,
            fontsize=10, verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path


def generate_mortality_curve_with_risk_table(
    matched_df: pd.DataFrame,
    output_path: Path,
    analysis_type: str = "main",
    time_col: str = "survival_time_28d",
    event_col: str = "death_28d",
    cox_results: dict = None
) -> Path:
    """
    Generate JAMA-style cumulative mortality curve with risk table and Hazard Ratio.

    Args:
        matched_df: Matched cohort data
        output_path: Path to save plot
        analysis_type: "main" or "sensitivity"
        time_col: Time column name
        event_col: Event column name
        cox_results: Cox regression results containing HR, CI, p-value

    Returns:
        Path to saved plot
    """
    # Prepare survival data
    df = matched_df.copy()

    # If using raw data, prepare survival variables
    if 'icu_intime' in df.columns and 'date_of_death' in df.columns:
        df['icu_intime'] = pd.to_datetime(df['icu_intime'])
        df['date_of_death'] = pd.to_datetime(df['date_of_death'], errors='coerce')
        df['days_to_death'] = (df['date_of_death'] - df['icu_intime']).dt.total_seconds() / (24 * 3600)

        df['survival_time_28d'] = np.where(
            df['days_to_death'].notna() & (df['days_to_death'] <= 28),
            df['days_to_death'],
            28
        )

        df['death_28d'] = np.where(
            df['days_to_death'].notna() & (df['days_to_death'] <= 28),
            1,
            0
        )

        # Round to daily bins for cleaner curves
        df['survival_time_28d'] = df['survival_time_28d'].round(0).clip(lower=0.01, upper=28)
        time_col = 'survival_time_28d'
        event_col = 'death_28d'

    treat_col = 'treatment_group' if 'treatment_group' in df.columns else 'treat'
    treatment = df[df[treat_col] == 1]
    control = df[df[treat_col] == 0]

    # Fit Kaplan-Meier
    kmf_treatment = KaplanMeierFitter()
    kmf_control = KaplanMeierFitter()

    kmf_treatment.fit(
        treatment[time_col],
        treatment[event_col],
        label='Treatment'
    )

    kmf_control.fit(
        control[time_col],
        control[event_col],
        label='Control'
    )

    # Create figure with risk table
    fig, (ax_main, ax_table) = plt.subplots(
        2, 1,
        figsize=(10, 8),
        gridspec_kw={'height_ratios': [4, 1], 'hspace': 0.05}
    )

    # Plot cumulative mortality (1 - survival)
    time_points_treatment = kmf_treatment.survival_function_.index
    time_points_control = kmf_control.survival_function_.index
    cumulative_mortality_treatment = 1 - kmf_treatment.survival_function_['Treatment']
    cumulative_mortality_control = 1 - kmf_control.survival_function_['Control']

    ax_main.step(time_points_treatment, cumulative_mortality_treatment, where='post',
                 linewidth=3.0, color='#E74C3C', label='Treatment')
    ax_main.step(time_points_control, cumulative_mortality_control, where='post',
                 linewidth=3.0, color='#3498DB', label='Control')

    ax_main.set_xlim(0, 28)
    ax_main.set_ylim(0, max(cumulative_mortality_treatment.max(),
                            cumulative_mortality_control.max()) * 1.1)
    ax_main.set_ylabel('Cumulative Mortality', fontsize=12, weight='bold')
    ax_main.set_title('28-Day Cumulative Mortality', fontsize=14, weight='bold')
    ax_main.legend(loc='upper left', fontsize=11, frameon=True)
    ax_main.grid(True, alpha=0.3, linestyle='--')
    ax_main.spines['top'].set_visible(False)
    ax_main.spines['right'].set_visible(False)

    # Add Hazard Ratio annotation if cox_results provided
    if cox_results is not None:
        hr = cox_results.get('hr')
        ci_lower = cox_results.get('ci_lower')
        ci_upper = cox_results.get('ci_upper')
        p_value = cox_results.get('p_value')
        
        if hr is not None:
            hr_text = f"Hazard Ratio: {hr:.2f}"
            if ci_lower is not None and ci_upper is not None:
                hr_text += f"\n95% CI: ({ci_lower:.2f}, {ci_upper:.2f})"
            if p_value is not None:
                hr_text += f"\np = {p_value:.4f}" if p_value >= 0.001 else "\np < 0.001"
            
            # Position in upper right corner with box
            ax_main.text(0.98, 0.98, hr_text,
                        transform=ax_main.transAxes,
                        fontsize=10,
                        verticalalignment='top',
                        horizontalalignment='right',
                        bbox=dict(boxstyle='round', facecolor='white', 
                                edgecolor='gray', alpha=0.9, pad=0.6))

    # Number at risk table
    risk_time_points = [0, 5, 10, 15, 20, 25, 28]

    ax_table.axis('off')
    ax_table.set_xlim(0, 28)
    ax_table.set_ylim(0, 2)

    # Table header
    ax_table.text(-1.5, 1.5, 'No. at Risk', fontsize=10, weight='bold', ha='right')

    # Treatment row
    ax_table.text(-1.5, 1.0, 'Treatment', fontsize=9, ha='right', color='#E74C3C')
    for t in risk_time_points:
        n_at_risk = (treatment[time_col] >= t).sum()
        ax_table.text(t, 1.0, str(n_at_risk), fontsize=9, ha='center')

    # Control row
    ax_table.text(-1.5, 0.5, 'Control', fontsize=9, ha='right', color='#3498DB')
    for t in risk_time_points:
        n_at_risk = (control[time_col] >= t).sum()
        ax_table.text(t, 0.5, str(n_at_risk), fontsize=9, ha='center')

    # Time axis labels
    ax_table.text(-1.5, 0, 'Days', fontsize=9, ha='right', style='italic')
    for t in risk_time_points:
        ax_table.text(t, 0, str(t), fontsize=9, ha='center', style='italic')

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path
