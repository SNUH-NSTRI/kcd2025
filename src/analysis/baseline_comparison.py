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
