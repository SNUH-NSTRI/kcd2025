"""
NCT 코호트에 Baseline Characteristics 병합

Usage:
    python scripts/merge_nct_with_baseline.py --nct-csv outputs/NCT03389555_hydrocortisone_v2.2.csv
"""

import argparse
import pandas as pd
import re
import sys
from pathlib import Path


def merge_nct_with_baseline(
    nct_csv: str,
    baseline_csv: str = None,
    output_csv: str = None
):
    print("=" * 80)
    print("NCT 코호트 + Baseline Characteristics 병합")
    print("=" * 80)

    # Always use v3.1 baseline
    if baseline_csv is None:
        version = "3.1"
        baseline_csv = f"cache/baseline_characteristics_v{version}_final.csv"
        print(f"Using baseline: {baseline_csv}")

    # Auto-generate output filename
    if output_csv is None:
        output_csv = nct_csv.replace('.csv', '_with_baseline.csv')
        print(f"Auto-generated output: {output_csv}")

    # Load NCT cohort
    print(f"\n1. Loading NCT cohort: {nct_csv}")
    nct_df = pd.read_csv(nct_csv)
    print(f"   Rows: {len(nct_df):,}")
    print(f"   Columns (original): {len(nct_df.columns)}")

    # Remove inclusion/exclusion criteria columns
    inclusion_exclusion_cols = [
        'included_adult', 'included_sepsis3_infection', 'included_vasopressor',
        'excluded_pregnancy', 'excluded_kidney_stones', 'excluded_esrd',
        'excluded_g6pd', 'excluded_hemochromatosis', 'excluded_early_death'
    ]
    cols_to_drop = [col for col in inclusion_exclusion_cols if col in nct_df.columns]
    if cols_to_drop:
        nct_df = nct_df.drop(columns=cols_to_drop)
        print(f"   Removed {len(cols_to_drop)} inclusion/exclusion columns")
        print(f"   Columns (after cleanup): {len(nct_df.columns)}")

    # Load baseline characteristics
    print(f"\n2. Loading baseline characteristics: {baseline_csv}")
    baseline_df = pd.read_csv(baseline_csv)
    print(f"   Rows: {len(baseline_df):,}")
    print(f"   Columns: {len(baseline_df.columns)}")

    # Filter baseline to only NCT cohort stays
    print(f"\n3. Filtering baseline to NCT cohort stay_ids...")
    nct_stay_ids = set(nct_df['stay_id'])
    baseline_filtered = baseline_df[baseline_df['stay_id'].isin(nct_stay_ids)]
    print(f"   Filtered rows: {len(baseline_filtered):,}")

    # Merge on stay_id
    print(f"\n4. Merging on stay_id...")
    merged_df = nct_df.merge(
        baseline_filtered,
        on='stay_id',
        how='left',
        suffixes=('', '_baseline')
    )

    # Handle duplicate columns
    # NCT has: subject_id, hadm_id, stay_id
    # Baseline has: subject_id, hadm_id, stay_id, intime, outtime, ...
    # Remove duplicates with '_baseline' suffix
    duplicate_cols = [c for c in merged_df.columns if c.endswith('_baseline')]
    if duplicate_cols:
        print(f"   Removing {len(duplicate_cols)} duplicate columns: {duplicate_cols[:5]}...")
        merged_df = merged_df.drop(columns=duplicate_cols)

    print(f"\n5. Final merged dataset:")
    print(f"   Rows: {len(merged_df):,}")
    print(f"   Columns: {len(merged_df.columns)}")
    print(f"   Missing baseline features: {merged_df['gender'].isna().sum():,} patients")

    # Save
    print(f"\n6. Saving to {output_csv}...")
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    merged_df.to_csv(output_csv, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("MERGE COMPLETE!")
    print("=" * 80)
    print(f"\nFinal feature count:")
    print(f"  NCT features: {len(nct_df.columns)}")
    print(f"  Baseline features: {len(baseline_filtered.columns) - 3}")  # Exclude join keys
    print(f"  Total features: {len(merged_df.columns)}")

    print(f"\nTreatment distribution:")
    print(merged_df['treatment_group'].value_counts().to_string())

    print(f"\nMortality rate:")
    print(f"  Overall: {merged_df['mortality'].mean():.1%}")
    print(f"  Treatment: {merged_df[merged_df['treatment_group'] == 1]['mortality'].mean():.1%}")
    print(f"  Control: {merged_df[merged_df['treatment_group'] == 0]['mortality'].mean():.1%}")

    return merged_df


def main():
    parser = argparse.ArgumentParser(
        description="Merge NCT cohort with baseline characteristics"
    )
    parser.add_argument(
        "--nct-csv",
        required=True,
        help="NCT cohort CSV file (e.g., NCT03389555_hydrocortisone_v2.2.csv)"
    )
    parser.add_argument(
        "--baseline-csv",
        help="Baseline characteristics CSV (auto-detected from nct-csv version if not provided)"
    )
    parser.add_argument(
        "--output",
        help="Output CSV file path (auto-generated if not provided)"
    )

    args = parser.parse_args()

    try:
        merge_nct_with_baseline(
            nct_csv=args.nct_csv,
            baseline_csv=args.baseline_csv,
            output_csv=args.output
        )
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
