#!/usr/bin/env python3
"""
실제 통합 예시: Trialist + Baseline Characteristics

이 스크립트는 feature_types_utils.py의 피처 타입 시스템이
어떻게 trialist 파이프라인과 통합되는지 실제 예시를 보여줍니다.
"""

import pandas as pd
import json
import sys
from pathlib import Path

# Import feature types utilities
sys.path.insert(0, str(Path(__file__).parent))
from feature_types_utils import (
    load_baseline_characteristics,
    get_feature_type,
    get_features_by_type,
    get_feature_info
)


def create_sample_trialist_output():
    """
    Trialist 파이프라인의 예시 출력 생성
    """
    return {
        "trial_id": "NCT03389555",
        "source_document": "VITAMINS Trial",
        "criteria": [
            {
                "type": "Inclusion",
                "original_text": "Age 18 years or older",
                "MIMIC": {
                    "vars1": "hosp.patients(anchor_age)",
                    "method1": "anchor_age >= 18"
                },
                "annotations": [
                    {"text_span": "Age", "domain": "Demographics"},
                    {"text_span": "18 years or older", "domain": "Value"}
                ]
            },
            {
                "type": "Inclusion",
                "original_text": "Septic shock diagnosis",
                "MIMIC": {
                    "vars1": "hosp.diagnoses_icd",
                    "method1": "ICD-10: R57.2; ICD-9: 785.52"
                },
                "annotations": [
                    {"text_span": "septic shock", "domain": "Condition"}
                ]
            },
            {
                "type": "Exclusion",
                "original_text": "Congestive heart failure",
                "MIMIC": {
                    "vars1": "hosp.diagnoses_icd",
                    "method1": "ICD-10: I50; ICD-9: 428"
                },
                "annotations": [
                    {"text_span": "Congestive heart failure", "domain": "Condition"}
                ]
            },
            {
                "type": "Exclusion",
                "original_text": "Lactate > 2.0 mmol/L",
                "MIMIC": {
                    "vars1": "hosp.labevents",
                    "method1": "lactate (itemid=50813) | Value: > 2.0 mmol/L"
                },
                "annotations": [
                    {"text_span": "Lactate", "domain": "Measurement"},
                    {"text_span": "> 2.0 mmol/L", "domain": "Value"}
                ]
            }
        ]
    }


def create_sample_baseline_data():
    """
    Baseline characteristics 샘플 데이터 생성
    """
    data = {
        'subject_id': [1, 2, 3, 4, 5, 6, 7, 8],
        'anchor_age': [65, 72, 45, 17, 55, 68, 80, 52],  # #4는 18세 미만
        'gender': ['M', 'F', 'M', 'M', 'F', 'F', 'M', 'F'],
        'temperature': [37.2, 38.5, 36.8, 37.0, 38.2, 37.5, 36.9, 37.8],
        'heart_rate': [85, 110, 78, 92, 105, 88, 75, 95],
        'lactate': [1.2, 2.5, 1.8, 1.5, 3.0, 1.1, 1.9, 1.6],  # #2, #5는 > 2.0
        'chf': [0, 0, 1, 0, 0, 1, 0, 0],  # #3, #6은 CHF 있음
        'mi': [1, 0, 0, 0, 1, 0, 0, 1],
        'diabetes': [1, 1, 0, 0, 1, 1, 0, 1],
        'gcs': [15, 12, 14, 15, 10, 13, 15, 14],
        'apache_ii': [12, 18, 10, 8, 22, 15, 14, 16],
    }

    df = pd.DataFrame(data)

    # ✅ 피처 타입에 맞게 dtype 수동 설정 (실제로는 load_baseline_characteristics()가 자동으로 함)
    df['anchor_age'] = df['anchor_age'].astype('float64')
    df['gender'] = df['gender'].astype('category')
    df['temperature'] = df['temperature'].astype('float64')
    df['heart_rate'] = df['heart_rate'].astype('float64')
    df['lactate'] = df['lactate'].astype('float64')
    df['chf'] = df['chf'].astype('Int8')
    df['mi'] = df['mi'].astype('Int8')
    df['diabetes'] = df['diabetes'].astype('Int8')
    df['gcs'] = df['gcs'].astype('Int16')
    df['apache_ii'] = df['apache_ii'].astype('Int16')

    return df


def apply_criterion_with_type_info(df: pd.DataFrame, criterion: dict) -> pd.DataFrame:
    """
    피처 타입 정보를 활용하여 criterion을 정확하게 적용

    이 함수가 feature_types_utils.py를 실제로 사용하는 부분입니다!
    """
    criterion_type = criterion['type']
    annotations = criterion['annotations']
    original_text = criterion['original_text']

    result = df.copy()

    print(f"\n{'🔵 INCLUSION' if criterion_type == 'Inclusion' else '🔴 EXCLUSION'}: {original_text}")
    print("-" * 70)

    # Demographics 처리
    for ann in annotations:
        domain = ann.get('domain', '').lower()
        text = ann.get('text_span', '').lower()

        if domain == 'demographics' and 'age' in text:
            # ✅ 피처 타입 확인
            feat_type = get_feature_type('anchor_age')
            feat_info = get_feature_info('anchor_age')

            print(f"  📊 Feature: anchor_age")
            print(f"     Type: {feat_type}")
            print(f"     Description: {feat_info['description']}")
            print(f"     Current dtype: {result['anchor_age'].dtype}")

            # 값 추출
            value_anns = [a for a in annotations if a.get('domain', '').lower() == 'value']
            if value_anns:
                import re
                v_text = value_anns[0].get('text_span', '')
                match = re.search(r'[≥>=]\s*(\d+)', v_text)

                if match:
                    threshold = int(match.group(1))
                    before = len(result)

                    if criterion_type == 'Inclusion':
                        # ✅ Continuous feature → numeric comparison
                        result = result[result['anchor_age'] >= threshold]
                        print(f"     Filter: anchor_age >= {threshold}")
                    else:
                        result = result[result['anchor_age'] < threshold]
                        print(f"     Filter: anchor_age < {threshold}")

                    after = len(result)
                    print(f"     Result: {before} → {after} patients (excluded: {before-after})")

    # Measurement 처리
    for ann in annotations:
        domain = ann.get('domain', '').lower()
        text = ann.get('text_span', '').lower()

        if domain == 'measurement' and 'lactate' in text:
            # ✅ 피처 타입 확인
            feat_type = get_feature_type('lactate')
            feat_info = get_feature_info('lactate')

            print(f"  📊 Feature: lactate")
            print(f"     Type: {feat_type}")
            print(f"     Unit: {feat_info['unit']}")
            print(f"     Current dtype: {result['lactate'].dtype}")

            # 값 추출
            value_anns = [a for a in annotations if a.get('domain', '').lower() == 'value']
            if value_anns:
                import re
                v_text = value_anns[0].get('text_span', '')
                match = re.search(r'>\s*(\d+\.?\d*)', v_text)

                if match:
                    threshold = float(match.group(1))
                    before = len(result)

                    if criterion_type == 'Inclusion':
                        # ✅ Continuous feature → numeric comparison
                        result = result[result['lactate'] > threshold]
                        print(f"     Filter: lactate > {threshold}")
                    else:
                        result = result[result['lactate'] <= threshold]
                        print(f"     Filter: lactate <= {threshold}")

                    after = len(result)
                    print(f"     Result: {before} → {after} patients (excluded: {before-after})")

    # Condition 처리 (Comorbidities - Binary features)
    for ann in annotations:
        domain = ann.get('domain', '').lower()
        text = ann.get('text_span', '').lower()

        if domain == 'condition' and 'heart failure' in text:
            # ✅ 피처 타입 확인
            feat_type = get_feature_type('chf')
            feat_info = get_feature_info('chf')

            print(f"  📊 Feature: chf (Congestive Heart Failure)")
            print(f"     Type: {feat_type}")
            print(f"     Description: {feat_info['description']}")
            print(f"     Current dtype: {result['chf'].dtype}")

            before = len(result)

            if criterion_type == 'Inclusion':
                # ✅ Binary feature → exact match (0 or 1)
                result = result[result['chf'] == 1]
                print(f"     Filter: chf == 1 (has CHF)")
            else:
                result = result[result['chf'] == 0]
                print(f"     Filter: chf == 0 (no CHF)")

            after = len(result)
            print(f"     Result: {before} → {after} patients (excluded: {before-after})")

    return result


def generate_cohort_statistics(df: pd.DataFrame, name: str):
    """
    피처 타입별로 적절한 통계량 생성

    이 함수도 feature_types_utils.py를 사용합니다!
    """
    print(f"\n{'='*70}")
    print(f"📊 {name} - STATISTICS BY FEATURE TYPE")
    print(f"{'='*70}")
    print(f"Total patients: {len(df)}")

    # Continuous features
    continuous = ['anchor_age', 'temperature', 'heart_rate', 'lactate']
    continuous_in_df = [f for f in continuous if f in df.columns]

    if continuous_in_df:
        print(f"\n📈 CONTINUOUS FEATURES (mean ± SD, median [IQR])")
        for feat in continuous_in_df:
            data = df[feat].dropna()
            feat_info = get_feature_info(feat)

            print(f"   {feat}:")
            print(f"      {feat_info['description']}")
            print(f"      mean ± SD: {data.mean():.1f} ± {data.std():.1f} {feat_info['unit'] or ''}")
            print(f"      median [IQR]: {data.median():.1f} [{data.quantile(0.25):.1f}, {data.quantile(0.75):.1f}]")

    # Binary features
    binary = ['chf', 'mi', 'diabetes']
    binary_in_df = [f for f in binary if f in df.columns]

    if binary_in_df:
        print(f"\n🔢 BINARY FEATURES (n (%))")
        for feat in binary_in_df:
            count = int(df[feat].sum())
            total = len(df[feat].dropna())
            pct = (count / total * 100) if total > 0 else 0
            feat_info = get_feature_info(feat)

            print(f"   {feat}: {count}/{total} ({pct:.1f}%) - {feat_info['description']}")

    # Categorical features
    if 'gender' in df.columns:
        print(f"\n🏷️  CATEGORICAL FEATURES (n (%))")
        feat_info = get_feature_info('gender')
        print(f"   gender - {feat_info['description']}")
        for cat, count in df['gender'].value_counts().items():
            pct = count / len(df['gender'].dropna()) * 100
            print(f"      {cat}: {count} ({pct:.1f}%)")

    # Ordinal features
    ordinal = ['gcs', 'apache_ii']
    ordinal_in_df = [f for f in ordinal if f in df.columns]

    if ordinal_in_df:
        print(f"\n📊 ORDINAL FEATURES (median [IQR], range)")
        for feat in ordinal_in_df:
            data = df[feat].dropna()
            feat_info = get_feature_info(feat)

            print(f"   {feat} - {feat_info['description']}")
            print(f"      median [IQR]: {data.median():.0f} [{data.quantile(0.25):.0f}, {data.quantile(0.75):.0f}]")
            print(f"      range: {data.min():.0f} - {data.max():.0f}")


def main():
    print("=" * 70)
    print("🔬 TRIALIST + BASELINE CHARACTERISTICS INTEGRATION EXAMPLE")
    print("=" * 70)
    print("\nThis example demonstrates how feature_types_utils.py is used")
    print("in the trialist pipeline for accurate data filtering and statistics.\n")

    # 1. Trialist 출력 준비
    trialist_output = create_sample_trialist_output()
    print(f"\n1️⃣ Trialist Pipeline Output:")
    print(f"   Trial ID: {trialist_output['trial_id']}")
    print(f"   Total criteria: {len(trialist_output['criteria'])}")

    # 2. Baseline characteristics 데이터 준비
    baseline_df = create_sample_baseline_data()
    print(f"\n2️⃣ Baseline Characteristics Data:")
    print(f"   Total patients: {len(baseline_df)}")
    print(f"   Features: {list(baseline_df.columns)}")

    # 초기 통계
    generate_cohort_statistics(baseline_df, "INITIAL COHORT")

    # 3. Inclusion criteria 적용
    print(f"\n{'='*70}")
    print("3️⃣ APPLYING INCLUSION CRITERIA")
    print(f"{'='*70}")

    result = baseline_df.copy()
    inclusion_criteria = [c for c in trialist_output['criteria'] if c['type'] == 'Inclusion']

    for criterion in inclusion_criteria:
        result = apply_criterion_with_type_info(result, criterion)

    generate_cohort_statistics(result, "AFTER INCLUSION CRITERIA")

    # 4. Exclusion criteria 적용
    print(f"\n{'='*70}")
    print("4️⃣ APPLYING EXCLUSION CRITERIA")
    print(f"{'='*70}")

    exclusion_criteria = [c for c in trialist_output['criteria'] if c['type'] == 'Exclusion']

    for criterion in exclusion_criteria:
        result = apply_criterion_with_type_info(result, criterion)

    # 최종 통계
    generate_cohort_statistics(result, "FINAL FILTERED COHORT")

    # 5. 요약
    print(f"\n{'='*70}")
    print("5️⃣ SUMMARY")
    print(f"{'='*70}")
    print(f"Initial cohort: {len(baseline_df)} patients")
    print(f"Final cohort: {len(result)} patients")
    print(f"Exclusion rate: {(1 - len(result)/len(baseline_df))*100:.1f}%")
    print()

    print("Excluded patients breakdown:")
    print(f"  - Age < 18: 1 patient (subject_id=4)")
    print(f"  - CHF: 2 patients (subject_id=3, 6)")
    print(f"  - Lactate > 2.0: 2 patients (subject_id=2, 5)")
    print(f"  Total excluded: {len(baseline_df) - len(result)} patients")
    print()

    print("✅ Final eligible patients:")
    print(result[['subject_id', 'anchor_age', 'lactate', 'chf']].to_string(index=False))

    print("\n" + "="*70)
    print("💡 KEY TAKEAWAY")
    print("="*70)
    print("feature_types_utils.py ensures:")
    print("  1. Correct data types for accurate filtering")
    print("  2. Appropriate statistical methods for each feature type")
    print("  3. Consistent type information across the entire pipeline")
    print("="*70)


if __name__ == "__main__":
    main()
