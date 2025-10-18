"""
Survival Analysis Module

생존분석(Kaplan-Meier, Cox proportional hazards)을 수행하는 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional, List
import matplotlib
# CRITICAL: Use non-interactive backend to prevent GUI thread issues in background tasks
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test
import warnings

warnings.filterwarnings('ignore')


def prepare_survival_data(
    treatment_df: pd.DataFrame,
    control_df: pd.DataFrame,
    time_column: str = 'los',
    event_column: Optional[str] = None,
    event_threshold: Optional[float] = None
) -> pd.DataFrame:
    """
    생존분석을 위한 데이터를 준비합니다.

    Args:
        treatment_df: 투약군 DataFrame
        control_df: 대조군 DataFrame
        time_column: 시간 변수 (예: 'los' - length of stay)
        event_column: 이벤트 변수 (None이면 apache_ii 사용)
        event_threshold: 이벤트 임계값 (apache_ii >= threshold이면 event=1)

    Returns:
        생존분석용 DataFrame (group, time, event 포함)
    """
    # 데이터 복사 및 그룹 표시
    treatment_copy = treatment_df.copy()
    control_copy = control_df.copy()

    treatment_copy['group'] = 'Treatment'
    control_copy['group'] = 'Control'

    # 데이터 결합
    combined_df = pd.concat([treatment_copy, control_copy], ignore_index=True)

    # 시간 변수 처리
    if time_column not in combined_df.columns:
        raise ValueError(f"Time column '{time_column}' not found in data")

    combined_df['time'] = combined_df[time_column]

    # 이벤트 변수 처리
    if event_column is not None:
        if event_column not in combined_df.columns:
            raise ValueError(f"Event column '{event_column}' not found in data")
        combined_df['event'] = combined_df[event_column]
    else:
        # apache_ii를 사용하여 이벤트 생성
        # apache_ii는 APACHE II mortality probability (0-100%)
        if 'apache_ii' in combined_df.columns:
            if event_threshold is None:
                event_threshold = 50  # 기본값: 50% 이상
            # APACHE II score가 높으면 (mortality probability 높으면) event = 1
            combined_df['event'] = (combined_df['apache_ii'] >= event_threshold).astype(int)
        else:
            # 기본값: 모든 환자가 이벤트 발생
            print("⚠ Warning: No event column found. Using all events = 1")
            combined_df['event'] = 1

    # 결측값 및 음수 제거
    combined_df = combined_df[
        (combined_df['time'].notna()) &
        (combined_df['time'] > 0) &
        (combined_df['event'].notna())
    ].copy()

    # ========================================================================
    # 28-day censoring: Clinical trials typically use 28-day mortality
    # Patients who survive beyond 28 days are censored at day 28
    # ========================================================================
    MAX_FOLLOW_UP_DAYS = 28

    # Store original time for reference
    combined_df['time_original'] = combined_df['time']

    # Count patients who will be censored
    n_censored = (combined_df['time'] > MAX_FOLLOW_UP_DAYS).sum()

    # Apply censoring: cap time at 28 days
    combined_df['time'] = combined_df['time'].clip(upper=MAX_FOLLOW_UP_DAYS)

    # Mark censored patients as non-events (they survived past day 28)
    # CRITICAL: Only censor if they survived beyond 28 days (event=0 or time > 28)
    combined_df.loc[combined_df['time_original'] > MAX_FOLLOW_UP_DAYS, 'event'] = 0

    print(f"\n✓ Survival data prepared")
    print(f"  - Total patients: {len(combined_df):,}")
    print(f"  - Treatment: {(combined_df['group'] == 'Treatment').sum():,}")
    print(f"  - Control: {(combined_df['group'] == 'Control').sum():,}")
    print(f"  - Events: {combined_df['event'].sum():,} ({combined_df['event'].mean()*100:.1f}%)")
    print(f"  - Mean follow-up time: {combined_df['time'].mean():.2f} days")
    print(f"  - Censored at {MAX_FOLLOW_UP_DAYS} days: {n_censored:,} patients")

    return combined_df


def kaplan_meier_analysis(
    survival_df: pd.DataFrame,
    time_col: str = 'time',
    event_col: str = 'event',
    group_col: str = 'group',
    alpha: float = 0.05,
    plot: bool = True,
    output_path: Optional[str] = None
) -> Dict:
    """
    Kaplan-Meier 생존분석을 수행합니다.

    Args:
        survival_df: 생존분석용 DataFrame
        time_col: 시간 변수명
        event_col: 이벤트 변수명
        group_col: 그룹 변수명
        alpha: 신뢰구간 수준
        plot: 그래프 생성 여부
        output_path: 그래프 저장 경로

    Returns:
        분석 결과 딕셔너리
    """
    print("\n" + "="*70)
    print("Kaplan-Meier Survival Analysis")
    print("="*70)

    groups = survival_df[group_col].unique()

    # Kaplan-Meier Fitter
    kmf_results = {}
    survival_tables = {}

    for group in groups:
        group_data = survival_df[survival_df[group_col] == group]

        kmf = KaplanMeierFitter(alpha=alpha)
        kmf.fit(
            durations=group_data[time_col],
            event_observed=group_data[event_col],
            label=group
        )

        kmf_results[group] = kmf
        survival_tables[group] = kmf.survival_function_

        # 중앙 생존 시간
        median_survival = kmf.median_survival_time_
        print(f"\n{group} Group:")
        print(f"  - N patients: {len(group_data):,}")
        print(f"  - N events: {group_data[event_col].sum():,}")
        print(f"  - Median survival time: {median_survival:.2f} days")

        # 특정 시점의 생존율
        if len(kmf.survival_function_) > 0:
            try:
                survival_30d = kmf.survival_function_at_times(30).values[0]
                survival_90d = kmf.survival_function_at_times(90).values[0]
                print(f"  - 30-day survival: {survival_30d*100:.1f}%")
                print(f"  - 90-day survival: {survival_90d*100:.1f}%")
            except:
                pass

    # Log-rank test (군간 비교)
    print("\n" + "-"*70)
    print("Log-rank Test (Group Comparison)")
    print("-"*70)

    if len(groups) == 2:
        group1_data = survival_df[survival_df[group_col] == groups[0]]
        group2_data = survival_df[survival_df[group_col] == groups[1]]

        results = logrank_test(
            durations_A=group1_data[time_col],
            durations_B=group2_data[time_col],
            event_observed_A=group1_data[event_col],
            event_observed_B=group2_data[event_col],
            alpha=alpha
        )

        print(f"\nTest statistic: {results.test_statistic:.4f}")
        print(f"P-value: {results.p_value:.4f}")

        if results.p_value < alpha:
            print(f"✓ Significant difference between groups (p < {alpha})")
        else:
            print(f"✗ No significant difference between groups (p >= {alpha})")
    else:
        results = None
        print("⚠ Log-rank test requires exactly 2 groups")

    # 그래프 생성
    if plot:
        plt.figure(figsize=(10, 6))

        for group in groups:
            kmf_results[group].plot_survival_function(
                ci_show=True,
                label=group
            )

        plt.xlabel('Time (days)', fontsize=12)
        plt.ylabel('Survival Probability', fontsize=12)
        plt.title('Kaplan-Meier Survival Curves', fontsize=14, fontweight='bold')
        plt.legend(loc='best')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"\n✓ Plot saved: {output_path}")
        else:
            plt.savefig('kaplan_meier_curve.png', dpi=300, bbox_inches='tight')
            print(f"\n✓ Plot saved: kaplan_meier_curve.png")

        plt.close()

    return {
        'kmf_results': kmf_results,
        'survival_tables': survival_tables,
        'logrank_test': results,
        'groups': groups
    }


def cox_proportional_hazards(
    survival_df: pd.DataFrame,
    time_col: str = 'time',
    event_col: str = 'event',
    treatment_col: str = 'group',
    covariates: Optional[List[str]] = None,
    alpha: float = 0.05
) -> Dict:
    """
    Cox Proportional Hazards 모델을 적합합니다.

    Args:
        survival_df: 생존분석용 DataFrame
        time_col: 시간 변수명
        event_col: 이벤트 변수명
        treatment_col: 치료 변수명
        covariates: 공변량 리스트
        alpha: 신뢰구간 수준

    Returns:
        분석 결과 딕셔너리
    """
    print("\n" + "="*70)
    print("Cox Proportional Hazards Model")
    print("="*70)

    # 데이터 준비
    cox_df = survival_df.copy()

    # Treatment를 이진 변수로 변환
    cox_df['treatment'] = (cox_df[treatment_col] == 'Treatment').astype(int)

    # 모델에 포함할 변수
    if covariates is None:
        # Univariate analysis (treatment only)
        model_vars = ['treatment']
    else:
        # Multivariate analysis (treatment + covariates)
        model_vars = ['treatment'] + covariates

    # 결측값 처리
    cox_df_clean = cox_df[[time_col, event_col] + model_vars].copy()

    for var in model_vars:
        if var not in cox_df_clean.columns:
            print(f"⚠ Warning: '{var}' not found in data, skipping")
            model_vars.remove(var)
            continue

        if cox_df_clean[var].isna().any():
            cox_df_clean[var].fillna(cox_df_clean[var].median(), inplace=True)

    cox_df_clean = cox_df_clean.dropna()

    print(f"\nModel includes {len(model_vars)} variable(s):")
    for i, var in enumerate(model_vars, 1):
        print(f"  {i}. {var}")

    print(f"\nSample size: {len(cox_df_clean):,} patients")

    # Cox 모델 적합
    cph = CoxPHFitter(alpha=alpha)
    cph.fit(
        cox_df_clean,
        duration_col=time_col,
        event_col=event_col
    )

    # 결과 출력
    print("\n" + "-"*70)
    print("Cox Model Results")
    print("-"*70)
    print(cph.summary)

    # Treatment effect 요약
    treatment_hr = np.exp(cph.params_['treatment'])
    treatment_ci = np.exp(cph.confidence_intervals_.loc['treatment'])
    treatment_p = cph.summary.loc['treatment', 'p']

    print("\n" + "="*70)
    print("Treatment Effect Summary")
    print("="*70)
    print(f"Hazard Ratio (HR): {treatment_hr:.3f}")
    print(f"95% CI: ({treatment_ci.iloc[0]:.3f}, {treatment_ci.iloc[1]:.3f})")
    print(f"P-value: {treatment_p:.4f}")

    if treatment_p < alpha:
        if treatment_hr < 1:
            print(f"\n✓ Treatment is associated with REDUCED hazard (protective effect)")
        else:
            print(f"\n✓ Treatment is associated with INCREASED hazard")
    else:
        print(f"\n✗ No significant treatment effect (p >= {alpha})")

    # Concordance index (C-index)
    c_index = cph.concordance_index_
    print(f"\nConcordance Index (C-index): {c_index:.3f}")

    return {
        'model': cph,
        'summary': cph.summary,
        'hr': treatment_hr,
        'ci': treatment_ci,
        'p_value': treatment_p,
        'c_index': c_index,
        'covariates': model_vars
    }


def perform_survival_analysis(
    treatment_df: pd.DataFrame,
    control_df: pd.DataFrame,
    time_column: str = 'los',
    event_column: Optional[str] = None,
    event_threshold: Optional[float] = None,
    covariates: Optional[List[str]] = None,
    alpha: float = 0.05,
    output_dir: str = "."
) -> Dict:
    """
    전체 생존분석을 수행하는 통합 함수입니다.

    Args:
        treatment_df: 투약군 DataFrame
        control_df: 대조군 DataFrame
        time_column: 시간 변수
        event_column: 이벤트 변수
        event_threshold: 이벤트 임계값
        covariates: Cox 모델 공변량
        alpha: 유의수준
        output_dir: 출력 디렉토리

    Returns:
        분석 결과 딕셔너리
    """
    print("\n" + "="*70)
    print("SURVIVAL ANALYSIS")
    print("="*70)

    # 1. 데이터 준비
    print("\n[Step 1/3] Preparing survival data...")
    survival_df = prepare_survival_data(
        treatment_df=treatment_df,
        control_df=control_df,
        time_column=time_column,
        event_column=event_column,
        event_threshold=event_threshold
    )

    # 2. Kaplan-Meier 분석
    print("\n[Step 2/3] Kaplan-Meier analysis...")
    km_results = kaplan_meier_analysis(
        survival_df=survival_df,
        alpha=alpha,
        plot=True,
        output_path=f"{output_dir}/kaplan_meier_curve.png"
    )

    # 3. Cox Proportional Hazards
    print("\n[Step 3/3] Cox proportional hazards model...")
    cox_results = cox_proportional_hazards(
        survival_df=survival_df,
        covariates=covariates,
        alpha=alpha
    )

    # 결과 저장
    survival_df.to_csv(f"{output_dir}/survival_data.csv", index=False)
    print(f"\n✓ Survival data saved: {output_dir}/survival_data.csv")

    results = {
        'survival_df': survival_df,
        'kaplan_meier': km_results,
        'cox_model': cox_results
    }

    return results


def perform_survival_analysis_unified(
    df: pd.DataFrame,
    time_column: str = 'outcome_days',
    event_column: str = 'mortality',
    group_column: str = 'treatment_group',
    covariates: Optional[List[str]] = None,
    alpha: float = 0.05,
    output_dir: str = "."
) -> Dict:
    """
    Wrapper function that accepts unified DataFrame and splits by treatment group.

    This function bridges the gap between workflow.py (which has unified matched DataFrame)
    and the original perform_survival_analysis() (which expects split DataFrames).

    Args:
        df: Unified DataFrame with treatment indicator column
        time_column: Time-to-event column name (default: 'outcome_days')
        event_column: Event indicator column name (default: 'mortality')
        group_column: Treatment group indicator column (default: 'treatment_group')
        covariates: List of covariate names for Cox model
        alpha: Significance level
        output_dir: Output directory for plots and results

    Returns:
        Dictionary with survival analysis results
    """
    # Determine treatment column name (support both 'treatment_group' and 'treat')
    treat_col = group_column if group_column in df.columns else 'treat'

    if treat_col not in df.columns:
        raise ValueError(f"Treatment column '{group_column}' not found in DataFrame. Available: {df.columns.tolist()}")

    # Split by treatment group and reset index
    treatment_df = df[df[treat_col] == 1].copy().reset_index(drop=True)
    control_df = df[df[treat_col] == 0].copy().reset_index(drop=True)

    print(f"\n[Survival Analysis Wrapper]")
    print(f"  Treatment group: {len(treatment_df)} patients")
    print(f"  Control group: {len(control_df)} patients")
    print(f"  Time column: {time_column}")
    print(f"  Event column: {event_column}")

    # Call original function with split DataFrames
    return perform_survival_analysis(
        treatment_df=treatment_df,
        control_df=control_df,
        time_column=time_column,
        event_column=event_column,
        event_threshold=None,  # Use binary event column directly
        covariates=covariates,
        alpha=alpha,
        output_dir=output_dir
    )


if __name__ == "__main__":
    print("Survival Analysis 모듈이 성공적으로 로드되었습니다.")
    print("\n사용 예시:")
    print("""
from src.analysis import perform_survival_analysis

# 생존분석 수행
results = perform_survival_analysis(
    treatment_df=matched_treatment,
    control_df=matched_control,
    time_column='los',
    event_column=None,  # apache_ii 사용
    event_threshold=50,
    covariates=['anchor_age', 'gender', 'charlson_score'],
    alpha=0.05,
    output_dir='output'
)

# 결과
# - Kaplan-Meier curves
# - Log-rank test
# - Cox model (HR & 95% CI)
""")


def create_survival_plot(
    df: pd.DataFrame,
    time_col: str,
    event_col: str,
    group_col: str,
    output_path: str,
    title: str = "Kaplan-Meier Survival Curve"
):
    """
    Create and save Kaplan-Meier survival plot.
    
    Args:
        df: Dataframe with survival data
        time_col: Column name for time-to-event
        event_col: Column name for event indicator
        group_col: Column name for group labels
        output_path: Path to save plot
        title: Plot title
    """
    from pathlib import Path
    import matplotlib.pyplot as plt
    from lifelines import KaplanMeierFitter
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Fit KM for each group
    kmf = KaplanMeierFitter()
    
    for group_name in df[group_col].unique():
        mask = df[group_col] == group_name
        kmf.fit(
            df.loc[mask, time_col],
            df.loc[mask, event_col],
            label=group_name
        )
        kmf.plot_survival_function(ax=ax)
    
    # Styling
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Days', fontsize=12)
    ax.set_ylabel('Survival Probability', fontsize=12)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
