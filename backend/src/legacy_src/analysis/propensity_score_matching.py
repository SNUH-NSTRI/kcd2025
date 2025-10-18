"""
Propensity Score Matching Module

Propensity Score를 사용하여 투약군과 대조군을 매칭하는 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')


def calculate_propensity_scores(
    treatment_df: pd.DataFrame,
    control_df: pd.DataFrame,
    covariates: List[str],
    model_type: str = 'logistic'
) -> Tuple[np.ndarray, np.ndarray, object]:
    """
    Propensity Score를 계산합니다.

    Args:
        treatment_df: 투약군 DataFrame
        control_df: 대조군 DataFrame
        covariates: 공변량(매칭에 사용할 변수) 리스트
        model_type: 모델 타입 (기본값: 'logistic')

    Returns:
        Tuple[treatment_ps, control_ps, model]:
            - treatment_ps: 투약군의 propensity score
            - control_ps: 대조군의 propensity score
            - model: 학습된 모델
    """
    # 데이터 결합
    treatment_df_copy = treatment_df.copy()
    control_df_copy = control_df.copy()

    treatment_df_copy['treatment'] = 1
    control_df_copy['treatment'] = 0

    combined_df = pd.concat([treatment_df_copy, control_df_copy], ignore_index=True)

    # 공변량 준비
    X = combined_df[covariates].copy()

    # 결측값 처리 (평균으로 대체)
    for col in X.columns:
        if X[col].isna().any():
            X[col].fillna(X[col].mean(), inplace=True)

    # 타겟 변수
    y = combined_df['treatment']

    # Propensity Score 모델 학습
    if model_type == 'logistic':
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X, y)
        ps = model.predict_proba(X)[:, 1]
    else:
        raise ValueError(f"Unsupported model type: {model_type}")

    # 투약군과 대조군의 propensity score 분리
    n_treatment = len(treatment_df)
    treatment_ps = ps[:n_treatment]
    control_ps = ps[n_treatment:]

    print(f"\n✓ Propensity scores calculated")
    print(f"  - Treatment group PS: mean={treatment_ps.mean():.3f}, std={treatment_ps.std():.3f}")
    print(f"  - Control group PS: mean={control_ps.mean():.3f}, std={control_ps.std():.3f}")

    return treatment_ps, control_ps, model


def perform_matching(
    treatment_df: pd.DataFrame,
    control_df: pd.DataFrame,
    treatment_ps: np.ndarray,
    control_ps: np.ndarray,
    matching_method: str = 'nearest',
    caliper: Optional[float] = 0.1,
    ratio: int = 1,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Propensity Score를 사용하여 매칭을 수행합니다.

    Args:
        treatment_df: 투약군 DataFrame
        control_df: 대조군 DataFrame
        treatment_ps: 투약군의 propensity score
        control_ps: 대조군의 propensity score
        matching_method: 매칭 방법 ('nearest', 'optimal')
        caliper: 최대 PS 차이 (None이면 제한 없음)
        ratio: 투약군 1명당 매칭할 대조군 수
        random_state: 랜덤 시드

    Returns:
        Tuple[matched_treatment_df, matched_control_df, matching_info]:
            - matched_treatment_df: 매칭된 투약군
            - matched_control_df: 매칭된 대조군
            - matching_info: 매칭 정보 딕셔너리
    """
    np.random.seed(random_state)

    # PS를 2D 배열로 변환
    treatment_ps_2d = treatment_ps.reshape(-1, 1)
    control_ps_2d = control_ps.reshape(-1, 1)

    if matching_method == 'nearest':
        # Nearest Neighbor Matching
        nn = NearestNeighbors(n_neighbors=ratio, metric='euclidean')
        nn.fit(control_ps_2d)

        distances, indices = nn.kneighbors(treatment_ps_2d)

        # Caliper 적용
        matched_treatment_indices = []
        matched_control_indices = []

        for i, (dists, idxs) in enumerate(zip(distances, indices)):
            valid_matches = []
            for dist, idx in zip(dists, idxs):
                if caliper is None or dist <= caliper:
                    valid_matches.append(idx)

            if len(valid_matches) > 0:
                matched_treatment_indices.append(i)
                matched_control_indices.extend(valid_matches)

        # 매칭된 데이터 추출
        matched_treatment_df = treatment_df.iloc[matched_treatment_indices].copy()
        matched_control_df = control_df.iloc[matched_control_indices].copy()

        # 매칭 정보
        matching_info = {
            'method': matching_method,
            'caliper': caliper,
            'ratio': ratio,
            'n_treatment_original': len(treatment_df),
            'n_control_original': len(control_df),
            'n_treatment_matched': len(matched_treatment_df),
            'n_control_matched': len(matched_control_df),
            'match_rate_treatment': len(matched_treatment_df) / len(treatment_df) * 100,
            'match_rate_control': len(matched_control_df) / len(control_df) * 100,
        }

    else:
        raise ValueError(f"Unsupported matching method: {matching_method}")

    print(f"\n✓ Matching completed")
    print(f"  - Method: {matching_method}")
    print(f"  - Caliper: {caliper}")
    print(f"  - Ratio: 1:{ratio}")
    print(f"  - Treatment: {matching_info['n_treatment_original']} → {matching_info['n_treatment_matched']} "
          f"({matching_info['match_rate_treatment']:.1f}%)")
    print(f"  - Control: {matching_info['n_control_original']} → {matching_info['n_control_matched']} "
          f"({matching_info['match_rate_control']:.1f}%)")

    return matched_treatment_df, matched_control_df, matching_info


def propensity_score_matching(
    treatment_df: pd.DataFrame,
    control_df: pd.DataFrame,
    covariates: List[str],
    matching_method: str = 'nearest',
    caliper: Optional[float] = 0.1,
    ratio: int = 1,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Propensity Score Matching을 수행하는 통합 함수입니다.

    Args:
        treatment_df: 투약군 DataFrame
        control_df: 대조군 DataFrame
        covariates: 매칭에 사용할 공변량 리스트
        matching_method: 매칭 방법 ('nearest')
        caliper: 최대 PS 차이 (표준편차의 배수, 일반적으로 0.1)
        ratio: 투약군 1명당 매칭할 대조군 수
        random_state: 랜덤 시드

    Returns:
        Tuple[matched_treatment_df, matched_control_df, result_info]:
            - matched_treatment_df: 매칭된 투약군 DataFrame
            - matched_control_df: 매칭된 대조군 DataFrame
            - result_info: 매칭 결과 정보 딕셔너리

    Example:
        >>> covariates = ['anchor_age', 'gender', 'bmi', 'heart_rate']
        >>> matched_tx, matched_ctrl, info = propensity_score_matching(
        ...     treatment_df=medicated_df,
        ...     control_df=control_df,
        ...     covariates=covariates,
        ...     caliper=0.1,
        ...     ratio=1
        ... )
    """
    print("="*70)
    print("Propensity Score Matching")
    print("="*70)
    print(f"\nCovariates used for matching ({len(covariates)}):")
    for i, cov in enumerate(covariates, 1):
        print(f"  {i}. {cov}")

    # 1. Propensity Score 계산
    print("\n[Step 1/2] Calculating propensity scores...")
    print("-" * 70)

    treatment_ps, control_ps, model = calculate_propensity_scores(
        treatment_df=treatment_df,
        control_df=control_df,
        covariates=covariates,
        model_type='logistic'
    )

    # 2. 매칭 수행
    print("\n[Step 2/2] Performing matching...")
    print("-" * 70)

    matched_treatment_df, matched_control_df, matching_info = perform_matching(
        treatment_df=treatment_df,
        control_df=control_df,
        treatment_ps=treatment_ps,
        control_ps=control_ps,
        matching_method=matching_method,
        caliper=caliper,
        ratio=ratio,
        random_state=random_state
    )

    # 3. 결과 정보
    result_info = {
        'covariates': covariates,
        'model': model,
        'treatment_ps': treatment_ps,
        'control_ps': control_ps,
        'matched_treatment_ps': treatment_ps[matched_treatment_df.index],
        'matched_control_ps': control_ps[matched_control_df.index],
        'matching_info': matching_info
    }

    print("\n" + "="*70)
    print("Propensity Score Matching Summary")
    print("="*70)
    print(f"Covariates: {len(covariates)}")
    print(f"Matching method: {matching_method}")
    print(f"Caliper: {caliper}")
    print(f"\nBefore matching:")
    print(f"  - Treatment: {matching_info['n_treatment_original']:,}")
    print(f"  - Control: {matching_info['n_control_original']:,}")
    print(f"\nAfter matching:")
    print(f"  - Treatment: {matching_info['n_treatment_matched']:,} "
          f"({matching_info['match_rate_treatment']:.1f}%)")
    print(f"  - Control: {matching_info['n_control_matched']:,} "
          f"({matching_info['match_rate_control']:.1f}%)")
    print("="*70)

    return matched_treatment_df, matched_control_df, result_info


def get_default_matching_covariates() -> List[str]:
    """
    기본 매칭 공변량 리스트를 반환합니다.

    Returns:
        공변량 리스트
    """
    covariates = [
        # Demographics
        'anchor_age',
        'bmi',

        # Vital signs
        'heart_rate',
        'sbp',
        'dbp',
        'respiratory_rate',
        'temperature',
        'spo2',

        # Comorbidities
        'chf',
        'mi',
        'diabetes',
        'ckd',
        'copd',
        'liver_disease',
        'cancer',

        # Severity scores
        'charlson_score',

        # Interventions
        'mechanical_ventilation',
        'any_vasopressor',
        'renal_replacement_therapy',
    ]

    return covariates


if __name__ == "__main__":
    # 예시 사용법
    print("Propensity Score Matching 모듈이 성공적으로 로드되었습니다.")
    print("\n사용 예시:")
    print("""
from src.analysis import propensity_score_matching, get_default_matching_covariates

# 매칭에 사용할 공변량
covariates = get_default_matching_covariates()

# PSM 수행
matched_treatment, matched_control, info = propensity_score_matching(
    treatment_df=medicated_df,
    control_df=control_df,
    covariates=covariates,
    caliper=0.1,
    ratio=1,
    random_state=42
)
""")
