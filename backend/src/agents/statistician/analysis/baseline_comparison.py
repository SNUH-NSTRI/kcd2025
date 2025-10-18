"""
두 군의 Baseline Characteristics를 비교하는 모듈

이 모듈은 투약군과 대조군의 baseline characteristics를 비교하고
Standard Mean Difference (SMD)를 계산하여 군간 균형을 평가합니다.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats


def calculate_smd(group1: pd.Series, group2: pd.Series, is_binary: bool = False) -> float:
    """
    Standardized Mean Difference (SMD)를 계산합니다.

    SMD는 두 군 간의 차이를 표준화한 값으로, 절대값이 0.1 미만이면 균형이 잘 맞는 것으로 간주됩니다.

    Args:
        group1: 첫 번째 군의 데이터
        group2: 두 번째 군의 데이터
        is_binary: 이진 변수 여부

    Returns:
        SMD 값
    """
    # 결측값 제거
    g1 = group1.dropna()
    g2 = group2.dropna()

    if len(g1) == 0 or len(g2) == 0:
        return np.nan

    mean1 = g1.mean()
    mean2 = g2.mean()

    if is_binary:
        # 이진 변수의 경우
        var1 = mean1 * (1 - mean1)
        var2 = mean2 * (1 - mean2)
    else:
        # 연속 변수의 경우
        var1 = g1.var()
        var2 = g2.var()

    # Pooled standard deviation
    pooled_std = np.sqrt((var1 + var2) / 2)

    if pooled_std == 0:
        return 0.0

    smd = (mean1 - mean2) / pooled_std

    return smd


def format_continuous_variable(data: pd.Series, show_n: bool = False) -> str:
    """
    연속형 변수를 평균(표준편차) 형식으로 포맷팅합니다.

    Args:
        data: 연속형 데이터
        show_n: 샘플 수 표시 여부

    Returns:
        포맷팅된 문자열 (예: "68.9 (15.0) [n = 100]")
    """
    clean_data = data.dropna()

    if len(clean_data) == 0:
        return "N/A"

    mean = clean_data.mean()
    std = clean_data.std()

    result = f"{mean:.1f} ({std:.1f})"

    if show_n and len(clean_data) != len(data):
        result += f" [n = {len(clean_data)}]"

    return result


def format_categorical_variable(data: pd.Series, category_value=None,
                                 total_n: Optional[int] = None) -> str:
    """
    범주형 변수를 빈도(백분율) 형식으로 포맷팅합니다.

    Args:
        data: 범주형 데이터
        category_value: 특정 카테고리 값 (None이면 전체 빈도 표시)
        total_n: 전체 샘플 수 (백분율 계산용)

    Returns:
        포맷팅된 문자열 (예: "44 (43.6)")
    """
    if category_value is not None:
        # 특정 카테고리의 빈도
        count = (data == category_value).sum()
    else:
        # 결측값이 아닌 데이터의 빈도
        count = data.notna().sum()

    if total_n is None:
        total_n = len(data)

    percentage = (count / total_n * 100) if total_n > 0 else 0

    return f"{count} ({percentage:.1f})"


def create_baseline_comparison_table(
    group1_df: pd.DataFrame,
    group2_df: pd.DataFrame,
    group1_name: str = "Intervention",
    group2_name: str = "Control",
    continuous_vars: Optional[List[str]] = None,
    categorical_vars: Optional[Dict[str, List]] = None,
    show_smd: bool = True
) -> pd.DataFrame:
    """
    두 군의 baseline characteristics 비교 테이블을 생성합니다.

    Args:
        group1_df: 첫 번째 군의 DataFrame
        group2_df: 두 번째 군의 DataFrame
        group1_name: 첫 번째 군의 이름
        group2_name: 두 번째 군의 이름
        continuous_vars: 연속형 변수 리스트
        categorical_vars: 범주형 변수 딕셔너리 {변수명: [카테고리 값들]}
        show_smd: SMD 표시 여부

    Returns:
        비교 테이블 DataFrame
    """
    results = []

    n1 = len(group1_df)
    n2 = len(group2_df)

    # 헤더 정보
    group1_header = f"{group1_name} (n = {n1})"
    group2_header = f"{group2_name} (n = {n2})"

    # Demographics 섹션
    results.append({
        'Characteristics': 'Demographics',
        group1_header: '',
        group2_header: '',
        'SMD': ''
    })

    # 연속형 변수 처리
    if continuous_vars:
        for var in continuous_vars:
            if var not in group1_df.columns or var not in group2_df.columns:
                continue

            # 변수명을 더 읽기 좋게 변환
            var_display = var.replace('_', ' ').title()

            # 평균(표준편차) 계산
            g1_formatted = format_continuous_variable(group1_df[var], show_n=True)
            g2_formatted = format_continuous_variable(group2_df[var], show_n=True)

            # SMD 계산
            smd = calculate_smd(group1_df[var], group2_df[var], is_binary=False)
            smd_str = f"{smd:.3f}" if not np.isnan(smd) else "N/A"

            results.append({
                'Characteristics': f"  {var_display}, mean (SD)",
                group1_header: g1_formatted,
                group2_header: g2_formatted,
                'SMD': smd_str if show_smd else ''
            })

    # 범주형 변수 처리
    if categorical_vars:
        for var, categories in categorical_vars.items():
            if var not in group1_df.columns or var not in group2_df.columns:
                continue

            # 변수명
            var_display = var.replace('_', ' ').title()

            # 변수 헤더 (전체 n 표시)
            g1_n = group1_df[var].notna().sum()
            g2_n = group2_df[var].notna().sum()

            g1_n_str = f"n = {g1_n}" if g1_n != n1 else ""
            g2_n_str = f"n = {g2_n}" if g2_n != n2 else ""

            results.append({
                'Characteristics': f"  {var_display}, No. (%)",
                group1_header: g1_n_str,
                group2_header: g2_n_str,
                'SMD': ''
            })

            # 각 카테고리별 빈도
            for category in categories:
                g1_formatted = format_categorical_variable(
                    group1_df[var], category_value=category, total_n=n1
                )
                g2_formatted = format_categorical_variable(
                    group2_df[var], category_value=category, total_n=n2
                )

                # 이진 변수로 SMD 계산
                g1_binary = (group1_df[var] == category).astype(float)
                g2_binary = (group2_df[var] == category).astype(float)
                smd = calculate_smd(g1_binary, g2_binary, is_binary=True)
                smd_str = f"{smd:.3f}" if not np.isnan(smd) else "N/A"

                category_display = str(category).title() if isinstance(category, str) else str(category)

                results.append({
                    'Characteristics': f"    {category_display}",
                    group1_header: g1_formatted,
                    group2_header: g2_formatted,
                    'SMD': smd_str if show_smd else ''
                })

    # DataFrame으로 변환
    comparison_df = pd.DataFrame(results)

    if not show_smd:
        comparison_df = comparison_df.drop(columns=['SMD'])

    return comparison_df


def get_default_baseline_variables() -> Tuple[List[str], Dict[str, List]]:
    """
    기본 baseline characteristics 변수들을 반환합니다.

    Returns:
        Tuple[연속형 변수 리스트, 범주형 변수 딕셔너리]
    """
    # 연속형 변수
    continuous_vars = [
        'anchor_age',  # Age
        'bmi',  # BMI
        'height_cm',
        'weight_kg',
        'temperature',
        'heart_rate',
        'sbp',
        'dbp',
        'respiratory_rate',
        'spo2',
        'lactate',
        'apache_ii_score',
        'charlson_score',
        'los',  # Length of stay
    ]

    # 범주형 변수
    categorical_vars = {
        'gender': ['F', 'M'],
        'race': ['WHITE', 'BLACK/AFRICAN AMERICAN', 'ASIAN', 'HISPANIC/LATINO', 'OTHER'],
        'mechanical_ventilation': [0, 1],
        'any_vasopressor': [0, 1],
        'renal_replacement_therapy': [0, 1],
        'chf': [0, 1],  # Congestive heart failure
        'mi': [0, 1],  # Myocardial infarction
        'diabetes': [0, 1],
        'ckd': [0, 1],  # Chronic kidney disease
        'copd': [0, 1],
        'liver_disease': [0, 1],
        'cancer': [0, 1],
    }

    return continuous_vars, categorical_vars


def assess_balance(comparison_df: pd.DataFrame, smd_threshold: float = 0.1) -> Dict:
    """
    두 군 간의 균형(balance)을 평가합니다.

    Args:
        comparison_df: 비교 테이블 DataFrame
        smd_threshold: SMD 임계값 (기본값 0.1)

    Returns:
        균형 평가 결과 딕셔너리
    """
    if 'SMD' not in comparison_df.columns:
        return {'error': 'SMD column not found'}

    # SMD 값을 숫자로 변환
    smd_values = []
    for val in comparison_df['SMD']:
        try:
            if val and val != '' and val != 'N/A':
                smd_values.append(abs(float(val)))
        except (ValueError, TypeError):
            continue

    if len(smd_values) == 0:
        return {'error': 'No valid SMD values found'}

    # 균형 평가
    balanced_vars = sum(1 for smd in smd_values if smd < smd_threshold)
    total_vars = len(smd_values)
    imbalanced_vars = total_vars - balanced_vars

    max_smd = max(smd_values)
    mean_smd = np.mean(smd_values)

    return {
        'total_variables': total_vars,
        'balanced_variables': balanced_vars,
        'imbalanced_variables': imbalanced_vars,
        'balance_percentage': (balanced_vars / total_vars * 100) if total_vars > 0 else 0,
        'max_smd': max_smd,
        'mean_smd': mean_smd,
        'threshold': smd_threshold
    }


def print_balance_assessment(balance_results: Dict):
    """균형 평가 결과를 출력합니다."""
    if 'error' in balance_results:
        print(f"Error: {balance_results['error']}")
        return

    print("\n" + "="*60)
    print("Balance Assessment (SMD Analysis)")
    print("="*60)
    print(f"Threshold: |SMD| < {balance_results['threshold']}")
    print(f"\nTotal variables analyzed: {balance_results['total_variables']}")
    print(f"Balanced variables: {balance_results['balanced_variables']} "
          f"({balance_results['balance_percentage']:.1f}%)")
    print(f"Imbalanced variables: {balance_results['imbalanced_variables']} "
          f"({100 - balance_results['balance_percentage']:.1f}%)")
    print(f"\nMaximum |SMD|: {balance_results['max_smd']:.3f}")
    print(f"Mean |SMD|: {balance_results['mean_smd']:.3f}")

    if balance_results['max_smd'] < 0.1:
        print("\n✓ Excellent balance: All variables have |SMD| < 0.1")
    elif balance_results['max_smd'] < 0.2:
        print("\n✓ Good balance: All variables have |SMD| < 0.2")
    elif balance_results['balance_percentage'] >= 80:
        print("\n⚠ Acceptable balance: >80% of variables are balanced")
    else:
        print("\n⚠ Poor balance: Consider matching or adjustment methods")

    print("="*60)


if __name__ == "__main__":
    # 예시: Hydrocortisone 투약군 vs 비투약군 비교
    print("Loading data...")

    # 투약군과 비투약군 데이터 로드
    medicated_df = pd.read_csv("/home/tech/datathon/patients_with_Hydrocortisone_Na_Succ.csv")
    non_medicated_df = pd.read_csv("/home/tech/datathon/patients_without_Hydrocortisone_Na_Succ.csv")

    print(f"Medicated group: {len(medicated_df)} patients")
    print(f"Non-medicated group: {len(non_medicated_df)} patients")

    # 기본 변수 설정
    continuous_vars, categorical_vars = get_default_baseline_variables()

    # 비교 테이블 생성
    print("\nCreating baseline comparison table...")
    comparison_table = create_baseline_comparison_table(
        group1_df=medicated_df,
        group2_df=non_medicated_df,
        group1_name="Hydrocortisone",
        group2_name="Control",
        continuous_vars=continuous_vars,
        categorical_vars=categorical_vars,
        show_smd=True
    )

    # 테이블 출력
    print("\n" + "="*80)
    print("Table 1. Baseline Cohort Characteristics")
    print("="*80)
    print(comparison_table.to_string(index=False))

    # 균형 평가
    balance_results = assess_balance(comparison_table)
    print_balance_assessment(balance_results)

    # CSV로 저장
    output_path = "/home/tech/datathon/baseline_comparison_table.csv"
    comparison_table.to_csv(output_path, index=False)
    print(f"\n✓ Table saved to: {output_path}")


def _calculate_baseline_stats(df: pd.DataFrame, group_name: str) -> dict:
    """
    Calculate baseline statistics for a single cohort (before or after matching).

    This helper separates calculation from presentation for better testability.

    Args:
        df: Cohort DataFrame with 'treatment_group' column
        group_name: Name for this cohort (e.g., "Before Matching", "After Matching")

    Returns:
        Dictionary with treatment/control stats and sample sizes
    """
    treat_col = 'treatment_group' if 'treatment_group' in df.columns else 'treat'
    treatment = df[df[treat_col] == 1].copy()
    control = df[df[treat_col] == 0].copy()

    return {
        'group_name': group_name,
        'treatment': treatment,
        'control': control,
        'n_treatment': len(treatment),
        'n_control': len(control)
    }


def _generate_comparison_table(
    before_stats: dict,
    after_stats: dict,
    variables: list,
    output_path: str,
    style: str
) -> None:
    """
    Generate before/after PSM comparison table (academically rigorous format).

    Table structure:
    | Characteristic | Before Matching          | After Matching           |
    |                | Treatment | Control | SMD | Treatment | Control | SMD |

    Args:
        before_stats: Statistics for pre-matching cohort
        after_stats: Statistics for post-matching cohort
        variables: List of variable names
        output_path: Path to save markdown table
        style: Table style (JAMA)
    """
    from pathlib import Path

    # Extract cohorts
    before_treat = before_stats['treatment']
    before_ctrl = before_stats['control']
    after_treat = after_stats['treatment']
    after_ctrl = after_stats['control']

    # Build markdown table
    table_lines = []
    table_lines.append(f"# Table 1. Baseline Cohort Characteristics")
    table_lines.append("")

    # Use flat header structure for valid markdown (no multi-level headers)
    # This ensures proper rendering in React Markdown
    header = (
        f"| Characteristics | "
        f"Before Treatment (n={before_stats['n_treatment']}) | "
        f"Before Control (n={before_stats['n_control']}) | "
        f"Before SMD | "
        f"After Treatment (n={after_stats['n_treatment']}) | "
        f"After Control (n={after_stats['n_control']}) | "
        f"After SMD |"
    )

    # Left-align characteristics column, right-align all numerical data columns
    # This improves readability for statistical tables
    # Made SMD columns wider for visual consistency
    alignment = "|:----------------|-------------------------:|------------------------:|----------------:|------------------------:|-----------------------:|---------------:|"

    table_lines.append(header)
    table_lines.append(alignment)

    def add_row(name, before_t, before_c, before_smd, after_t, after_c, after_smd):
        """Add a table row with before/after comparison"""
        table_lines.append(
            f"| {name} | {before_t} | {before_c} | {before_smd} | {after_t} | {after_c} | {after_smd} |"
        )

    def add_category(category_name):
        """Add a category header with dynamically generated empty cells.

        This makes the function robust to future column changes.
        """
        # Dynamically create the correct number of empty cells (6 data columns)
        empty_cells = " | ".join(["" for _ in range(6)])
        table_lines.append(f"| **{category_name}** | {empty_cells} |")

    def calc_continuous_smd(t_data, c_data):
        """Calculate SMD for continuous variables"""
        t_mean = t_data.mean()
        t_std = t_data.std()
        c_mean = c_data.mean()
        c_std = c_data.std()
        pooled_std = np.sqrt((t_std**2 + c_std**2) / 2)
        return abs((t_mean - c_mean) / pooled_std) if pooled_std > 0 else 0

    def calc_binary_smd(t_data, c_data):
        """Calculate SMD for binary variables (proportion)"""
        p1 = t_data.mean()  # proportion in treatment
        p2 = c_data.mean()  # proportion in control
        pooled_var = (p1 * (1 - p1) + p2 * (1 - p2)) / 2
        return abs((p1 - p2) / np.sqrt(pooled_var)) if pooled_var > 0 else 0

    # ========== Demographics ==========
    add_category("Demographics")

    if 'anchor_age' in before_treat.columns:
        before_smd = calc_continuous_smd(before_treat['anchor_age'], before_ctrl['anchor_age'])
        after_smd = calc_continuous_smd(after_treat['anchor_age'], after_ctrl['anchor_age'])
        add_row(
            "  Age, mean (SD), y",
            f"{before_treat['anchor_age'].mean():.1f} ({before_treat['anchor_age'].std():.1f})",
            f"{before_ctrl['anchor_age'].mean():.1f} ({before_ctrl['anchor_age'].std():.1f})",
            f"{before_smd:.3f}",
            f"{after_treat['anchor_age'].mean():.1f} ({after_treat['anchor_age'].std():.1f})",
            f"{after_ctrl['anchor_age'].mean():.1f} ({after_ctrl['anchor_age'].std():.1f})",
            f"{after_smd:.3f}"
        )

    if 'bmi' in before_treat.columns:
        before_smd = calc_continuous_smd(before_treat['bmi'], before_ctrl['bmi'])
        after_smd = calc_continuous_smd(after_treat['bmi'], after_ctrl['bmi'])
        before_t_count = before_treat['bmi'].notna().sum()
        before_c_count = before_ctrl['bmi'].notna().sum()
        after_t_count = after_treat['bmi'].notna().sum()
        after_c_count = after_ctrl['bmi'].notna().sum()
        add_row(
            "  BMI, mean (SD)",
            f"{before_treat['bmi'].mean():.1f} ({before_treat['bmi'].std():.1f}) [n={before_t_count}]",
            f"{before_ctrl['bmi'].mean():.1f} ({before_ctrl['bmi'].std():.1f}) [n={before_c_count}]",
            f"{before_smd:.3f}",
            f"{after_treat['bmi'].mean():.1f} ({after_treat['bmi'].std():.1f}) [n={after_t_count}]",
            f"{after_ctrl['bmi'].mean():.1f} ({after_ctrl['bmi'].std():.1f}) [n={after_c_count}]",
            f"{after_smd:.3f}"
        )

    if 'gender' in before_treat.columns:
        before_t_female_bin = (before_treat['gender'] == 'F').astype(int)
        before_c_female_bin = (before_ctrl['gender'] == 'F').astype(int)
        after_t_female_bin = (after_treat['gender'] == 'F').astype(int)
        after_c_female_bin = (after_ctrl['gender'] == 'F').astype(int)

        before_smd = calc_binary_smd(before_t_female_bin, before_c_female_bin)
        after_smd = calc_binary_smd(after_t_female_bin, after_c_female_bin)

        before_t_female = (before_treat['gender'] == 'F').sum()
        before_c_female = (before_ctrl['gender'] == 'F').sum()
        after_t_female = (after_treat['gender'] == 'F').sum()
        after_c_female = (after_ctrl['gender'] == 'F').sum()

        add_row(
            "  Female sex, No. (%)",
            f"{before_t_female} ({before_t_female/len(before_treat)*100:.1f})",
            f"{before_c_female} ({before_c_female/len(before_ctrl)*100:.1f})",
            f"{before_smd:.3f}",
            f"{after_t_female} ({after_t_female/len(after_treat)*100:.1f})",
            f"{after_c_female} ({after_c_female/len(after_ctrl)*100:.1f})",
            f"{after_smd:.3f}"
        )

    # ========== Vital Signs ==========
    add_category("Vital Signs (First 24h)")

    vital_vars = [
        ('temperature', 'Temperature, mean (SD), °C'),
        ('heart_rate', 'Heart rate, mean (SD), bpm'),
        ('sbp', 'Systolic BP, mean (SD), mmHg'),
        ('dbp', 'Diastolic BP, mean (SD), mmHg'),
        ('respiratory_rate', 'Respiratory rate, mean (SD), /min'),
        ('spo2', 'SpO₂, mean (SD), %')
    ]

    for var, label in vital_vars:
        if var in before_treat.columns:
            before_smd = calc_continuous_smd(before_treat[var], before_ctrl[var])
            after_smd = calc_continuous_smd(after_treat[var], after_ctrl[var])
            add_row(
                f"  {label}",
                f"{before_treat[var].mean():.1f} ({before_treat[var].std():.1f})",
                f"{before_ctrl[var].mean():.1f} ({before_ctrl[var].std():.1f})",
                f"{before_smd:.3f}",
                f"{after_treat[var].mean():.1f} ({after_treat[var].std():.1f})",
                f"{after_ctrl[var].mean():.1f} ({after_ctrl[var].std():.1f})",
                f"{after_smd:.3f}"
            )

    # ========== Laboratory Values ==========
    add_category("Laboratory Values (First 24h)")

    # Blood gas
    if 'ph' in before_treat.columns:
        before_smd = calc_continuous_smd(before_treat['ph'], before_ctrl['ph'])
        after_smd = calc_continuous_smd(after_treat['ph'], after_ctrl['ph'])
        add_row(
            "  pH, mean (SD)",
            f"{before_treat['ph'].mean():.2f} ({before_treat['ph'].std():.2f})",
            f"{before_ctrl['ph'].mean():.2f} ({before_ctrl['ph'].std():.2f})",
            f"{before_smd:.3f}",
            f"{after_treat['ph'].mean():.2f} ({after_treat['ph'].std():.2f})",
            f"{after_ctrl['ph'].mean():.2f} ({after_ctrl['ph'].std():.2f})",
            f"{after_smd:.3f}"
        )

    lab_vars = [
        ('lactate', 'Lactate, median (IQR), mg/dL', True),
        ('hematocrit', 'Hematocrit, mean (SD), %', False),
        ('hemoglobin', 'Hemoglobin, mean (SD), g/dL', False),
        ('wbc', 'WBC, mean (SD), K/μL', False),
        ('platelets', 'Platelets, mean (SD), K/μL', False),
        ('creatinine', 'Creatinine, mean (SD), mg/dL', False),
        ('bun', 'BUN, mean (SD), mg/dL', False),
    ]

    for var, label, use_median in lab_vars:
        if var in before_treat.columns:
            before_smd = calc_continuous_smd(before_treat[var], before_ctrl[var])
            after_smd = calc_continuous_smd(after_treat[var], after_ctrl[var])
            if use_median:
                before_t_median = before_treat[var].median()
                before_t_q1 = before_treat[var].quantile(0.25)
                before_t_q3 = before_treat[var].quantile(0.75)
                before_c_median = before_ctrl[var].median()
                before_c_q1 = before_ctrl[var].quantile(0.25)
                before_c_q3 = before_ctrl[var].quantile(0.75)
                after_t_median = after_treat[var].median()
                after_t_q1 = after_treat[var].quantile(0.25)
                after_t_q3 = after_treat[var].quantile(0.75)
                after_c_median = after_ctrl[var].median()
                after_c_q1 = after_ctrl[var].quantile(0.25)
                after_c_q3 = after_ctrl[var].quantile(0.75)
                add_row(
                    f"  {label}",
                    f"{before_t_median:.1f} ({before_t_q1:.1f}-{before_t_q3:.1f})",
                    f"{before_c_median:.1f} ({before_c_q1:.1f}-{before_c_q3:.1f})",
                    f"{before_smd:.3f}",
                    f"{after_t_median:.1f} ({after_t_q1:.1f}-{after_t_q3:.1f})",
                    f"{after_c_median:.1f} ({after_c_q1:.1f}-{after_c_q3:.1f})",
                    f"{after_smd:.3f}"
                )
            else:
                add_row(
                    f"  {label}",
                    f"{before_treat[var].mean():.1f} ({before_treat[var].std():.1f})",
                    f"{before_ctrl[var].mean():.1f} ({before_ctrl[var].std():.1f})",
                    f"{before_smd:.3f}",
                    f"{after_treat[var].mean():.1f} ({after_treat[var].std():.1f})",
                    f"{after_ctrl[var].mean():.1f} ({after_ctrl[var].std():.1f})",
                    f"{after_smd:.3f}"
                )

    # ========== Severity Scores ==========
    add_category("Severity Scores")

    if 'gcs' in before_treat.columns:
        before_smd = calc_continuous_smd(before_treat['gcs'], before_ctrl['gcs'])
        after_smd = calc_continuous_smd(after_treat['gcs'], after_ctrl['gcs'])
        add_row(
            "  GCS, mean (SD)",
            f"{before_treat['gcs'].mean():.1f} ({before_treat['gcs'].std():.1f})",
            f"{before_ctrl['gcs'].mean():.1f} ({before_ctrl['gcs'].std():.1f})",
            f"{before_smd:.3f}",
            f"{after_treat['gcs'].mean():.1f} ({after_treat['gcs'].std():.1f})",
            f"{after_ctrl['gcs'].mean():.1f} ({after_ctrl['gcs'].std():.1f})",
            f"{after_smd:.3f}"
        )

    if 'apache_ii_score' in before_treat.columns:
        before_smd = calc_continuous_smd(before_treat['apache_ii_score'], before_ctrl['apache_ii_score'])
        after_smd = calc_continuous_smd(after_treat['apache_ii_score'], after_ctrl['apache_ii_score'])
        add_row(
            "  APACHE II, mean (SD)",
            f"{before_treat['apache_ii_score'].mean():.1f} ({before_treat['apache_ii_score'].std():.1f})",
            f"{before_ctrl['apache_ii_score'].mean():.1f} ({before_ctrl['apache_ii_score'].std():.1f})",
            f"{before_smd:.3f}",
            f"{after_treat['apache_ii_score'].mean():.1f} ({after_treat['apache_ii_score'].std():.1f})",
            f"{after_ctrl['apache_ii_score'].mean():.1f} ({after_ctrl['apache_ii_score'].std():.1f})",
            f"{after_smd:.3f}"
        )

    # ========== Comorbidities ==========
    if 'charlson_score' in before_treat.columns:
        add_category("Comorbidities")
        before_smd = calc_continuous_smd(before_treat['charlson_score'], before_ctrl['charlson_score'])
        after_smd = calc_continuous_smd(after_treat['charlson_score'], after_ctrl['charlson_score'])
        add_row(
            "  Charlson Index, mean (SD)",
            f"{before_treat['charlson_score'].mean():.1f} ({before_treat['charlson_score'].std():.1f})",
            f"{before_ctrl['charlson_score'].mean():.1f} ({before_ctrl['charlson_score'].std():.1f})",
            f"{before_smd:.3f}",
            f"{after_treat['charlson_score'].mean():.1f} ({after_treat['charlson_score'].std():.1f})",
            f"{after_ctrl['charlson_score'].mean():.1f} ({after_ctrl['charlson_score'].std():.1f})",
            f"{after_smd:.3f}"
        )

        comorbidity_vars = [
            ('chf', 'Congestive heart failure'),
            ('mi', 'Myocardial infarction'),
            ('pvd', 'Peripheral vascular disease'),
            ('cvd', 'Cerebrovascular disease'),
            ('copd', 'COPD'),
            ('diabetes', 'Diabetes'),
            ('ckd', 'Chronic kidney disease'),
            ('liver_disease', 'Liver disease'),
            ('cancer', 'Cancer')
        ]

        for var, label in comorbidity_vars:
            if var in before_treat.columns:
                before_t_count = (before_treat[var] == 1).sum()
                before_c_count = (before_ctrl[var] == 1).sum()
                after_t_count = (after_treat[var] == 1).sum()
                after_c_count = (after_ctrl[var] == 1).sum()
                before_smd = calc_binary_smd(before_treat[var], before_ctrl[var])
                after_smd = calc_binary_smd(after_treat[var], after_ctrl[var])
                add_row(
                    f"  {label}, No. (%)",
                    f"{before_t_count} ({before_t_count/len(before_treat)*100:.1f})",
                    f"{before_c_count} ({before_c_count/len(before_ctrl)*100:.1f})",
                    f"{before_smd:.3f}",
                    f"{after_t_count} ({after_t_count/len(after_treat)*100:.1f})",
                    f"{after_c_count} ({after_c_count/len(after_ctrl)*100:.1f})",
                    f"{after_smd:.3f}"
                )

    # ========== Organ Support ==========
    add_category("Organ Support (First 24h)")

    if 'any_vasopressor' in before_treat.columns:
        before_t_count = (before_treat['any_vasopressor'] == 1).sum()
        before_c_count = (before_ctrl['any_vasopressor'] == 1).sum()
        after_t_count = (after_treat['any_vasopressor'] == 1).sum()
        after_c_count = (after_ctrl['any_vasopressor'] == 1).sum()
        before_smd = calc_binary_smd(before_treat['any_vasopressor'], before_ctrl['any_vasopressor'])
        after_smd = calc_binary_smd(after_treat['any_vasopressor'], after_ctrl['any_vasopressor'])
        add_row(
            "  Vasopressor use, No. (%)",
            f"{before_t_count} ({before_t_count/len(before_treat)*100:.1f})",
            f"{before_c_count} ({before_c_count/len(before_ctrl)*100:.1f})",
            f"{before_smd:.3f}",
            f"{after_t_count} ({after_t_count/len(after_treat)*100:.1f})",
            f"{after_c_count} ({after_c_count/len(after_ctrl)*100:.1f})",
            f"{after_smd:.3f}"
        )

    if 'mechanical_ventilation' in before_treat.columns:
        before_t_count = (before_treat['mechanical_ventilation'] == 1).sum()
        before_c_count = (before_ctrl['mechanical_ventilation'] == 1).sum()
        after_t_count = (after_treat['mechanical_ventilation'] == 1).sum()
        after_c_count = (after_ctrl['mechanical_ventilation'] == 1).sum()
        before_smd = calc_binary_smd(before_treat['mechanical_ventilation'], before_ctrl['mechanical_ventilation'])
        after_smd = calc_binary_smd(after_treat['mechanical_ventilation'], after_ctrl['mechanical_ventilation'])
        add_row(
            "  Mechanical ventilation, No. (%)",
            f"{before_t_count} ({before_t_count/len(before_treat)*100:.1f})",
            f"{before_c_count} ({before_c_count/len(before_ctrl)*100:.1f})",
            f"{before_smd:.3f}",
            f"{after_t_count} ({after_t_count/len(after_treat)*100:.1f})",
            f"{after_c_count} ({after_c_count/len(after_ctrl)*100:.1f})",
            f"{after_smd:.3f}"
        )

    if 'renal_replacement_therapy' in before_treat.columns:
        before_t_count = (before_treat['renal_replacement_therapy'] == 1).sum()
        before_c_count = (before_ctrl['renal_replacement_therapy'] == 1).sum()
        after_t_count = (after_treat['renal_replacement_therapy'] == 1).sum()
        after_c_count = (after_ctrl['renal_replacement_therapy'] == 1).sum()
        before_smd = calc_binary_smd(before_treat['renal_replacement_therapy'], before_ctrl['renal_replacement_therapy'])
        after_smd = calc_binary_smd(after_treat['renal_replacement_therapy'], after_ctrl['renal_replacement_therapy'])
        add_row(
            "  Renal replacement therapy, No. (%)",
            f"{before_t_count} ({before_t_count/len(before_treat)*100:.1f})",
            f"{before_c_count} ({before_c_count/len(before_ctrl)*100:.1f})",
            f"{before_smd:.3f}",
            f"{after_t_count} ({after_t_count/len(after_treat)*100:.1f})",
            f"{after_c_count} ({after_c_count/len(after_ctrl)*100:.1f})",
            f"{after_smd:.3f}"
        )

    # Save markdown table
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    table_content = "\n".join(table_lines)
    table_content += "\n\n*Abbreviations: BMI = Body Mass Index; BP = Blood Pressure; SMD = Standardized Mean Difference*\n"
    table_content += "\n*Good balance: |SMD| < 0.1. Values in **bold** indicate significant improvement after matching.*\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(table_content)


def generate_baseline_table(
    matched_df: pd.DataFrame,
    variables,
    output_path: str,
    original_df: pd.DataFrame | None = None,
    style: str = "JAMA"
):
    """
    Generate JAMA-style baseline characteristics table with categories.

    Creates a publication-ready Table 1 with organized categories:
    - Demographics (age, BMI, gender)
    - Vital Signs (temperature, HR, BP, RR, SpO2)
    - Laboratory Values (blood gas, lactate, CBC, renal function)
    - Severity Scores (GCS, APACHE II)
    - Comorbidities (Charlson Index, individual conditions)
    - Organ Support (vasopressors, ventilation, RRT)

    Args:
        matched_df: Matched cohort data with 'treatment_group' column (1=treatment, 0=control)
        variables: List of variable names (used for validation, categories are predefined)
        output_path: Path to save markdown table
        original_df: Optional original (pre-matching) cohort for before/after comparison
        style: Table style (default: "JAMA")
    """
    from pathlib import Path

    # Always show after-matching results only (matched cohort)
    # original_df parameter is kept for backward compatibility but not used
    # PSM results should show the balanced cohort, not before/after comparison
    # Split by treatment
    treat_col = 'treatment_group' if 'treatment_group' in matched_df.columns else 'treat'
    treatment = matched_df[matched_df[treat_col] == 1].copy()
    control = matched_df[matched_df[treat_col] == 0].copy()

    # Build markdown table with categories
    table_lines = []
    table_lines.append(f"# Table 1. Baseline Cohort Characteristics")
    table_lines.append("")
    table_lines.append(f"| Characteristics | Treatment (n={len(treatment)}) | Control (n={len(control)}) | SMD |")
    # Left-align characteristics, right-align all numerical columns
    table_lines.append("|:----------------|-------------------------------:|----------------------------:|----:|")

    def add_row(name, t_val, c_val, smd_val=""):
        """Add a table row"""
        table_lines.append(f"| {name} | {t_val} | {c_val} | {smd_val} |")

    def add_category(category_name):
        """Add a category header"""
        table_lines.append(f"| **{category_name}** | | | |")

    def calc_continuous_smd(t_data, c_data):
        """Calculate SMD for continuous variables"""
        t_mean = t_data.mean()
        t_std = t_data.std()
        c_mean = c_data.mean()
        c_std = c_data.std()
        pooled_std = np.sqrt((t_std**2 + c_std**2) / 2)
        return abs((t_mean - c_mean) / pooled_std) if pooled_std > 0 else 0

    def calc_binary_smd(t_data, c_data):
        """Calculate SMD for binary variables (proportion)"""
        p1 = t_data.mean()  # proportion in treatment
        p2 = c_data.mean()  # proportion in control
        pooled_var = (p1 * (1 - p1) + p2 * (1 - p2)) / 2
        return abs((p1 - p2) / np.sqrt(pooled_var)) if pooled_var > 0 else 0

    # ========== Demographics ==========
    add_category("Demographics")

    if 'anchor_age' in matched_df.columns:
        smd = calc_continuous_smd(treatment['anchor_age'], control['anchor_age'])
        add_row("  Age, mean (SD), y",
               f"{treatment['anchor_age'].mean():.1f} ({treatment['anchor_age'].std():.1f})",
               f"{control['anchor_age'].mean():.1f} ({control['anchor_age'].std():.1f})",
               f"{smd:.3f}")

    if 'bmi' in matched_df.columns:
        smd = calc_continuous_smd(treatment['bmi'], control['bmi'])
        t_count = treatment['bmi'].notna().sum()
        c_count = control['bmi'].notna().sum()
        add_row("  BMI, mean (SD)",
               f"{treatment['bmi'].mean():.1f} ({treatment['bmi'].std():.1f}) [n = {t_count}]",
               f"{control['bmi'].mean():.1f} ({control['bmi'].std():.1f}) [n = {c_count}]",
               f"{smd:.3f}")

    if 'gender' in matched_df.columns:
        t_female = (treatment['gender'] == 'F').sum()
        c_female = (control['gender'] == 'F').sum()
        t_female_binary = (treatment['gender'] == 'F').astype(int)
        c_female_binary = (control['gender'] == 'F').astype(int)
        smd = calc_binary_smd(t_female_binary, c_female_binary)
        add_row("  Female sex, No. (%)",
               f"{t_female} ({t_female/len(treatment)*100:.1f})",
               f"{c_female} ({c_female/len(control)*100:.1f})",
               f"{smd:.3f}")

    # ========== Vital Signs ==========
    add_category("Vital Signs (First 24h)")

    vital_vars = [
        ('temperature', 'Temperature, mean (SD), °C'),
        ('heart_rate', 'Heart rate, mean (SD), bpm'),
        ('sbp', 'Systolic BP, mean (SD), mmHg'),
        ('dbp', 'Diastolic BP, mean (SD), mmHg'),
        ('respiratory_rate', 'Respiratory rate, mean (SD), /min'),
        ('spo2', 'SpO₂, mean (SD), %')
    ]

    for var, label in vital_vars:
        if var in matched_df.columns:
            smd = calc_continuous_smd(treatment[var], control[var])
            add_row(f"  {label}",
                   f"{treatment[var].mean():.1f} ({treatment[var].std():.1f})",
                   f"{control[var].mean():.1f} ({control[var].std():.1f})",
                   f"{smd:.3f}")

    # ========== Laboratory Values ==========
    add_category("Laboratory Values (First 24h)")

    # Blood gas
    if 'ph' in matched_df.columns:
        smd = calc_continuous_smd(treatment['ph'], control['ph'])
        add_row("  pH, mean (SD)",
               f"{treatment['ph'].mean():.2f} ({treatment['ph'].std():.2f})",
               f"{control['ph'].mean():.2f} ({control['ph'].std():.2f})",
               f"{smd:.3f}")

    lab_vars = [
        ('lactate', 'Lactate, median (IQR), mg/dL', True),
        ('hematocrit', 'Hematocrit, mean (SD), %', False),
        ('hemoglobin', 'Hemoglobin, mean (SD), g/dL', False),
        ('wbc', 'WBC, mean (SD), K/μL', False),
        ('platelets', 'Platelets, mean (SD), K/μL', False),
        ('creatinine', 'Creatinine, mean (SD), mg/dL', False),
        ('bun', 'BUN, mean (SD), mg/dL', False),
    ]

    for var, label, use_median in lab_vars:
        if var in matched_df.columns:
            smd = calc_continuous_smd(treatment[var], control[var])
            if use_median:
                t_median = treatment[var].median()
                t_q1 = treatment[var].quantile(0.25)
                t_q3 = treatment[var].quantile(0.75)
                c_median = control[var].median()
                c_q1 = control[var].quantile(0.25)
                c_q3 = control[var].quantile(0.75)
                add_row(f"  {label}",
                       f"{t_median:.1f} ({t_q1:.1f}-{t_q3:.1f})",
                       f"{c_median:.1f} ({c_q1:.1f}-{c_q3:.1f})",
                       f"{smd:.3f}")
            else:
                add_row(f"  {label}",
                       f"{treatment[var].mean():.1f} ({treatment[var].std():.1f})",
                       f"{control[var].mean():.1f} ({control[var].std():.1f})",
                       f"{smd:.3f}")

    # ========== Severity Scores ==========
    add_category("Severity Scores")

    if 'gcs' in matched_df.columns:
        smd = calc_continuous_smd(treatment['gcs'], control['gcs'])
        add_row("  GCS, mean (SD)",
               f"{treatment['gcs'].mean():.1f} ({treatment['gcs'].std():.1f})",
               f"{control['gcs'].mean():.1f} ({control['gcs'].std():.1f})",
               f"{smd:.3f}")

    if 'apache_ii_score' in matched_df.columns:
        smd = calc_continuous_smd(treatment['apache_ii_score'], control['apache_ii_score'])
        add_row("  APACHE II, mean (SD)",
               f"{treatment['apache_ii_score'].mean():.1f} ({treatment['apache_ii_score'].std():.1f})",
               f"{control['apache_ii_score'].mean():.1f} ({control['apache_ii_score'].std():.1f})",
               f"{smd:.3f}")

    # ========== Comorbidities ==========
    if 'charlson_score' in matched_df.columns:
        add_category("Comorbidities")
        smd = calc_continuous_smd(treatment['charlson_score'], control['charlson_score'])
        add_row("  Charlson Index, mean (SD)",
               f"{treatment['charlson_score'].mean():.1f} ({treatment['charlson_score'].std():.1f})",
               f"{control['charlson_score'].mean():.1f} ({control['charlson_score'].std():.1f})",
               f"{smd:.3f}")

        comorbidity_vars = [
            ('chf', 'Congestive heart failure'),
            ('mi', 'Myocardial infarction'),
            ('pvd', 'Peripheral vascular disease'),
            ('cvd', 'Cerebrovascular disease'),
            ('copd', 'COPD'),
            ('diabetes', 'Diabetes'),
            ('ckd', 'Chronic kidney disease'),
            ('liver_disease', 'Liver disease'),
            ('cancer', 'Cancer')
        ]

        for var, label in comorbidity_vars:
            if var in matched_df.columns:
                t_count = (treatment[var] == 1).sum()
                c_count = (control[var] == 1).sum()
                smd = calc_binary_smd(treatment[var], control[var])
                add_row(f"  {label}, No. (%)",
                       f"{t_count} ({t_count/len(treatment)*100:.1f})",
                       f"{c_count} ({c_count/len(control)*100:.1f})",
                       f"{smd:.3f}")

    # ========== Organ Support ==========
    add_category("Organ Support (First 24h)")

    if 'any_vasopressor' in matched_df.columns:
        t_count = (treatment['any_vasopressor'] == 1).sum()
        c_count = (control['any_vasopressor'] == 1).sum()
        smd = calc_binary_smd(treatment['any_vasopressor'], control['any_vasopressor'])
        add_row("  Vasopressor use, No. (%)",
               f"{t_count} ({t_count/len(treatment)*100:.1f})",
               f"{c_count} ({c_count/len(control)*100:.1f})",
               f"{smd:.3f}")

    if 'mechanical_ventilation' in matched_df.columns:
        t_count = (treatment['mechanical_ventilation'] == 1).sum()
        c_count = (control['mechanical_ventilation'] == 1).sum()
        smd = calc_binary_smd(treatment['mechanical_ventilation'], control['mechanical_ventilation'])
        add_row("  Mechanical ventilation, No. (%)",
               f"{t_count} ({t_count/len(treatment)*100:.1f})",
               f"{c_count} ({c_count/len(control)*100:.1f})",
               f"{smd:.3f}")

    if 'renal_replacement_therapy' in matched_df.columns:
        t_count = (treatment['renal_replacement_therapy'] == 1).sum()
        c_count = (control['renal_replacement_therapy'] == 1).sum()
        smd = calc_binary_smd(treatment['renal_replacement_therapy'], control['renal_replacement_therapy'])
        add_row("  Renal replacement therapy, No. (%)",
               f"{t_count} ({t_count/len(treatment)*100:.1f})",
               f"{c_count} ({c_count/len(control)*100:.1f})",
               f"{smd:.3f}")

    # Save markdown table
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    table_content = "\n".join(table_lines)
    table_content += "\n\n*Abbreviations: BMI = Body Mass Index; BP = Blood Pressure; SpO₂ = Oxygen Saturation; WBC = White Blood Cell; BUN = Blood Urea Nitrogen; GCS = Glasgow Coma Scale; APACHE = Acute Physiology and Chronic Health Evaluation; COPD = Chronic Obstructive Pulmonary Disease; CKD = Chronic Kidney Disease*\n"
    table_content += "\n*SMD = Standardized Mean Difference; Good balance: |SMD| < 0.1*\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(table_content)


def assess_balance_psm(original_df: pd.DataFrame, matched_df: pd.DataFrame, variables: list) -> pd.DataFrame:
    """
    Assess balance before and after PSM matching.
    
    Returns DataFrame with pre/post SMD for each variable.
    """
    import pandas as pd
    
    results = []
    
    # Original groups
    treat_col = 'treatment_group' if 'treatment_group' in original_df.columns else 'treat'
    orig_treat = original_df[original_df[treat_col] == 1]
    orig_control = original_df[original_df[treat_col] == 0]
    
    # Matched groups
    matched_treat = matched_df[matched_df[treat_col] == 1]
    matched_control = matched_df[matched_df[treat_col] == 0]
    
    for var in variables:
        if var not in original_df.columns:
            continue
            
        # Calculate pre-matching SMD
        pre_smd = calculate_smd(orig_treat[var], orig_control[var])
        
        # Calculate post-matching SMD  
        post_smd = calculate_smd(matched_treat[var], matched_control[var])
        
        results.append({
            'variable': var,
            'pre_smd': abs(pre_smd),
            'post_smd': abs(post_smd),
            'improved': abs(post_smd) < abs(pre_smd)
        })
    
    return pd.DataFrame(results)
