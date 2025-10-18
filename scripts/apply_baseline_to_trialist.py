#!/usr/bin/env python3
"""
Baseline Characteristics Integration with Trialist Pipeline

이 스크립트는 trialist 파이프라인의 출력(MIMIC 매핑 결과)을
실제 baseline characteristics 데이터와 결합하여 환자 필터링을 수행합니다.

Usage:
    python scripts/apply_baseline_to_trialist.py \
        --trialist-output trialist_result.json \
        --baseline-csv cache/baseline_characteristics.csv \
        --output filtered_cohort.csv
"""

import json
import pandas as pd
from pathlib import Path
import argparse
from typing import Dict, List, Any
import sys

# Feature types utility import
sys.path.insert(0, str(Path(__file__).parent))
from feature_types_utils import (
    load_baseline_characteristics,
    get_feature_type,
    get_features_by_type,
    print_feature_summary
)


class TrialistBaselineIntegrator:
    """
    Trialist 파이프라인 결과와 Baseline Characteristics를 통합하는 클래스
    """

    def __init__(self, trialist_json: Dict[str, Any], baseline_df: pd.DataFrame):
        """
        Args:
            trialist_json: Trialist 파이프라인의 최종 JSON 출력
            baseline_df: Baseline characteristics DataFrame (자동 타입 적용됨)
        """
        self.trialist = trialist_json
        self.baseline = baseline_df

        print("=" * 80)
        print("🔗 TRIALIST-BASELINE INTEGRATION INITIALIZED")
        print("=" * 80)
        print(f"📊 Baseline patients: {len(baseline_df):,}")
        print(f"📋 Trial criteria count: {len(trialist_json.get('criteria', []))}")
        print()

    def _map_criterion_to_baseline_filter(self, criterion: Dict) -> callable:
        """
        단일 criterion을 baseline characteristics 필터 함수로 변환

        Args:
            criterion: {
                "type": "Inclusion" | "Exclusion",
                "original_text": "Age ≥ 18 years",
                "MIMIC": {"vars1": "...", "method1": "..."},
                "annotations": [...]
            }

        Returns:
            필터 함수: lambda df: df[df['age'] >= 18]
        """
        criterion_type = criterion.get("type")
        original_text = criterion.get("original_text", "")
        annotations = criterion.get("annotations", [])
        mimic_info = criterion.get("MIMIC", {})

        filters = []

        # 1. Demographics 처리 (나이, 성별)
        for ann in annotations:
            domain = ann.get("domain", "").lower()
            text = ann.get("text_span", "")

            if domain == "demographics":
                # 나이 필터링
                if "age" in text.lower():
                    # Value annotation에서 조건 추출
                    value_anns = [a for a in annotations if a.get("domain", "").lower() == "value"]
                    for v_ann in value_anns:
                        v_text = v_ann.get("text_span", "")

                        # "≥ 18" 또는 ">= 18" 파싱
                        if "≥" in v_text or ">=" in v_text:
                            import re
                            match = re.search(r'[≥>=]\s*(\d+)', v_text)
                            if match:
                                threshold = int(match.group(1))
                                if criterion_type == "Inclusion":
                                    filters.append(lambda df, t=threshold: df[df['anchor_age'] >= t])
                                else:
                                    filters.append(lambda df, t=threshold: df[df['anchor_age'] < t])

                        elif "<" in v_text:
                            import re
                            match = re.search(r'<\s*(\d+)', v_text)
                            if match:
                                threshold = int(match.group(1))
                                if criterion_type == "Inclusion":
                                    filters.append(lambda df, t=threshold: df[df['anchor_age'] < t])
                                else:
                                    filters.append(lambda df, t=threshold: df[df['anchor_age'] >= t])

                # 성별 필터링
                elif "gender" in text.lower() or "male" in text.lower() or "female" in text.lower():
                    if "female" in text.lower():
                        if criterion_type == "Inclusion":
                            filters.append(lambda df: df[df['gender'] == 'F'])
                        else:
                            filters.append(lambda df: df[df['gender'] != 'F'])
                    elif "male" in text.lower() and "female" not in text.lower():
                        if criterion_type == "Inclusion":
                            filters.append(lambda df: df[df['gender'] == 'M'])
                        else:
                            filters.append(lambda df: df[df['gender'] != 'M'])

        # 2. Measurement 처리 (lab values, vital signs)
        for ann in annotations:
            domain = ann.get("domain", "").lower()
            text = ann.get("text_span", "").lower()

            if domain == "measurement":
                # lactate 필터링 예시
                if "lactate" in text:
                    value_anns = [a for a in annotations if a.get("domain", "").lower() == "value"]
                    for v_ann in value_anns:
                        v_text = v_ann.get("text_span", "")
                        import re

                        if ">" in v_text:
                            match = re.search(r'>\s*(\d+\.?\d*)', v_text)
                            if match:
                                threshold = float(match.group(1))
                                if criterion_type == "Inclusion":
                                    filters.append(lambda df, t=threshold: df[df['lactate'] > t])
                                else:
                                    filters.append(lambda df, t=threshold: df[df['lactate'] <= t])

        # 3. Condition 처리 (comorbidities - binary features)
        binary_features = get_features_by_type('binary')

        for ann in annotations:
            domain = ann.get("domain", "").lower()
            text = ann.get("text_span", "").lower()

            if domain == "condition":
                # CHF (Congestive Heart Failure)
                if "heart failure" in text or "chf" in text:
                    if criterion_type == "Inclusion":
                        filters.append(lambda df: df[df['chf'] == 1])
                    else:
                        filters.append(lambda df: df[df['chf'] == 0])

                # MI (Myocardial Infarction)
                elif "myocardial infarction" in text or "mi" in text:
                    if criterion_type == "Inclusion":
                        filters.append(lambda df: df[df['mi'] == 1])
                    else:
                        filters.append(lambda df: df[df['mi'] == 0])

                # 다른 comorbidity 매핑도 동일한 패턴으로 추가 가능

        # 모든 필터를 결합하는 최종 함수 반환
        def combined_filter(df: pd.DataFrame) -> pd.DataFrame:
            result = df.copy()
            for f in filters:
                result = f(result)
            return result

        return combined_filter

    def apply_criteria(self, verbose: bool = True) -> pd.DataFrame:
        """
        모든 Inclusion/Exclusion criteria를 baseline characteristics에 적용

        Returns:
            필터링된 환자 cohort DataFrame
        """
        result = self.baseline.copy()
        initial_count = len(result)

        print("🔍 APPLYING TRIAL CRITERIA TO BASELINE CHARACTERISTICS")
        print("=" * 80)

        # Inclusion criteria 먼저 적용
        inclusion_criteria = [c for c in self.trialist.get('criteria', []) if c.get('type') == 'Inclusion']
        for idx, criterion in enumerate(inclusion_criteria, 1):
            filter_func = self._map_criterion_to_baseline_filter(criterion)
            before = len(result)
            result = filter_func(result)
            after = len(result)

            if verbose:
                print(f"✅ Inclusion #{idx}: {criterion.get('original_text', '')[:60]}...")
                print(f"   Patients: {before:,} → {after:,} (excluded: {before-after:,})")

        print()

        # Exclusion criteria 적용
        exclusion_criteria = [c for c in self.trialist.get('criteria', []) if c.get('type') == 'Exclusion']
        for idx, criterion in enumerate(exclusion_criteria, 1):
            filter_func = self._map_criterion_to_baseline_filter(criterion)
            before = len(result)
            result = filter_func(result)
            after = len(result)

            if verbose:
                print(f"❌ Exclusion #{idx}: {criterion.get('original_text', '')[:60]}...")
                print(f"   Patients: {before:,} → {after:,} (excluded: {before-after:,})")

        print()
        print("=" * 80)
        print(f"📊 FINAL COHORT SUMMARY")
        print("=" * 80)
        print(f"Initial patients: {initial_count:,}")
        print(f"Final cohort: {len(result):,}")
        print(f"Exclusion rate: {(1 - len(result)/initial_count)*100:.1f}%")
        print()

        return result

    def generate_cohort_report(self, cohort_df: pd.DataFrame) -> Dict[str, Any]:
        """
        필터링된 cohort의 baseline characteristics 요약 통계 생성

        피처 타입에 따라 적절한 통계량 계산:
        - Continuous: mean ± SD, median [IQR]
        - Binary: n (%)
        - Categorical: n (%) per category
        - Ordinal: median [IQR], n (%) per level
        """
        report = {
            "cohort_size": len(cohort_df),
            "demographics": {},
            "vital_signs": {},
            "lab_values": {},
            "comorbidities": {},
            "severity_scores": {}
        }

        # Continuous features
        continuous = get_features_by_type('continuous')
        for feat in continuous:
            if feat not in cohort_df.columns:
                continue

            data = cohort_df[feat].dropna()
            if len(data) == 0:
                continue

            stats = {
                "mean": float(data.mean()),
                "std": float(data.std()),
                "median": float(data.median()),
                "q25": float(data.quantile(0.25)),
                "q75": float(data.quantile(0.75)),
                "missing": int(cohort_df[feat].isna().sum())
            }

            # 카테고리별로 분류
            if feat in ['anchor_age']:
                report['demographics'][feat] = stats
            elif feat in ['temperature', 'heart_rate', 'sbp', 'dbp', 'mbp', 'resp_rate', 'spo2']:
                report['vital_signs'][feat] = stats
            elif feat in ['ph', 'po2', 'pco2', 'lactate', 'glucose', 'bun', 'creatinine',
                          'sodium', 'potassium', 'chloride', 'hematocrit', 'hemoglobin',
                          'wbc', 'platelets', 'd_dimer', 'pt', 'aptt']:
                report['lab_values'][feat] = stats

        # Binary features (comorbidities)
        binary = get_features_by_type('binary')
        for feat in binary:
            if feat not in cohort_df.columns:
                continue

            count = int(cohort_df[feat].sum())
            total = int((~cohort_df[feat].isna()).sum())
            pct = (count / total * 100) if total > 0 else 0

            report['comorbidities'][feat] = {
                "n": count,
                "total": total,
                "percentage": round(pct, 1),
                "missing": int(cohort_df[feat].isna().sum())
            }

        # Categorical features
        categorical = get_features_by_type('categorical')
        for feat in categorical:
            if feat not in cohort_df.columns:
                continue

            value_counts = cohort_df[feat].value_counts()
            total = len(cohort_df[feat].dropna())

            report['demographics'][feat] = {
                cat: {
                    "n": int(count),
                    "percentage": round(count / total * 100, 1) if total > 0 else 0
                }
                for cat, count in value_counts.items()
            }

        # Ordinal features (severity scores)
        ordinal = get_features_by_type('ordinal')
        for feat in ordinal:
            if feat not in cohort_df.columns:
                continue

            data = cohort_df[feat].dropna()
            if len(data) == 0:
                continue

            report['severity_scores'][feat] = {
                "median": float(data.median()),
                "q25": float(data.quantile(0.25)),
                "q75": float(data.quantile(0.75)),
                "min": float(data.min()),
                "max": float(data.max()),
                "missing": int(cohort_df[feat].isna().sum())
            }

        return report


def main():
    parser = argparse.ArgumentParser(description='Integrate Trialist output with Baseline Characteristics')
    parser.add_argument('--trialist-output', required=True, help='Path to trialist JSON output')
    parser.add_argument('--baseline-csv', required=True, help='Path to baseline characteristics CSV')
    parser.add_argument('--output-cohort', required=True, help='Path to save filtered cohort CSV')
    parser.add_argument('--output-report', help='Path to save cohort report JSON (optional)')

    args = parser.parse_args()

    # 1. Load trialist output
    print(f"📥 Loading trialist output: {args.trialist_output}")
    with open(args.trialist_output, 'r', encoding='utf-8') as f:
        trialist_json = json.load(f)

    # 2. Load baseline characteristics with automatic type conversion
    print(f"📥 Loading baseline characteristics: {args.baseline_csv}")
    baseline_df = load_baseline_characteristics(args.baseline_csv)

    print("\n📋 Feature types summary:")
    print_feature_summary()
    print()

    # 3. Integrate and apply criteria
    integrator = TrialistBaselineIntegrator(trialist_json, baseline_df)
    filtered_cohort = integrator.apply_criteria(verbose=True)

    # 4. Save filtered cohort
    print(f"💾 Saving filtered cohort to: {args.output_cohort}")
    filtered_cohort.to_csv(args.output_cohort, index=False)

    # 5. Generate and save report
    if args.output_report:
        print(f"📊 Generating cohort report...")
        report = integrator.generate_cohort_report(filtered_cohort)

        with open(args.output_report, 'w', encoding='utf-8') as f:
            json.dumps(report, f, indent=2, ensure_ascii=False)

        print(f"💾 Report saved to: {args.output_report}")

    print("\n✅ Integration complete!")


if __name__ == "__main__":
    main()
