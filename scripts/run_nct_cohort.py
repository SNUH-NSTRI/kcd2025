#!/usr/bin/env python3
"""
Run NCT Cohort Extraction with Dynamic Treatment Medication

Executes NCT SQL with treatment medication as a parameter.
"""

import argparse
import duckdb
import pandas as pd
import re
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.cohort.utils import find_medication_family, generate_drug_values_cte


def run_nct_cohort(
    sql_file: str,
    treatment_med: str,
    output: str = None,
    mimic_version: str = "3.1",
    verbose: bool = True
) -> pd.DataFrame:
    """
    Execute NCT SQL with dynamic treatment medication.

    Args:
        sql_file: Path to NCT SQL file
        treatment_med: Treatment medication name
        output: Output CSV path (auto-generated if None)
        mimic_version: MIMIC-IV version (default: 3.1)
        verbose: Print progress

    Returns:
        DataFrame with cohort
    """
    start_time = time.time()

    # Auto-generate output filename if not provided
    if output is None:
        # Extract NCT number from SQL file
        nct_match = re.search(r'NCT\d+', sql_file)
        nct_number = nct_match.group(0) if nct_match else 'NCTXXXXX'

        # Clean medication name for filename (alphanumeric only)
        med_clean = re.sub(r'[^a-zA-Z0-9]', '', treatment_med.lower())

        # Generate output path: project/{NCT}/cohorts/{medication}/
        output = f"project/{nct_number}/cohorts/{med_clean}/{nct_number}_{med_clean}_v{mimic_version}.csv"

        # Create directory if it doesn't exist
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if verbose:
            print(f"Auto-generated output: {output}")

    # Step 1: Read SQL template
    if verbose:
        print("Step 1: Reading NCT SQL template...")
    with open(sql_file, 'r') as f:
        sql_template = f.read()

    # Step 2: Find medication family for exclusion logic
    if verbose:
        print("Step 2: Finding medication family for exclusion...")

    try:
        family_name, family_variants = find_medication_family(
            treatment_med,
            'config/metadata/medicines_variants.yaml'
        )
        if verbose:
            print(f"         Medication family: {family_name}")
            print(f"         Family has {len(family_variants)} variants")
            print(f"         Treatment (exact): {treatment_med.lower()}")
    except Exception as e:
        if verbose:
            print(f"⚠️  Warning: {e}")
            print(f"   Using treatment medication as standalone (no family exclusion)")
        family_name = treatment_med.lower()
        family_variants = [treatment_med.lower()]

    # Step 3: Generate SQL CTEs
    if verbose:
        print("Step 3: Generating SQL CTEs...")

    # Exact treatment medication (for treatment group)
    exact_treatment_cte = generate_drug_values_cte([treatment_med.lower()])

    # All family variants (for exclusion from control group)
    family_exclusion_cte = generate_drug_values_cte(family_variants)

    # Step 4: Replace placeholders in SQL template
    if verbose:
        print("Step 4: Injecting medication patterns into SQL...")

    # Replace MIMIC version
    sql = sql_template.replace('{{MIMIC_VERSION}}', mimic_version)

    # Replace treatment medication (exact match)
    sql = sql.replace('{{TREATMENT_MED_EXACT}}', exact_treatment_cte)

    # Replace family variants (for exclusion)
    sql = sql.replace('{{FAMILY_VARIANTS_CTE}}', family_exclusion_cte)

    # Step 5: Execute query
    if verbose:
        print("Step 5: Executing NCT cohort extraction...")
        print("         (This may take a few minutes...)")

    con = duckdb.connect()
    df = con.execute(sql).df()
    con.close()

    elapsed = time.time() - start_time

    # Step 6: Calculate summary statistics
    total = len(df)
    treatment_count = df[df['treatment_group'] == 1].shape[0] if 'treatment_group' in df.columns else 0
    control_count = df[df['treatment_group'] == 0].shape[0] if 'treatment_group' in df.columns else 0
    mortality_count = df[df['mortality'] == 1].shape[0] if 'mortality' in df.columns else 0

    treatment_pct = (treatment_count / total * 100) if total > 0 else 0
    control_pct = (control_count / total * 100) if total > 0 else 0
    mortality_pct = (mortality_count / total * 100) if total > 0 else 0

    # Check exclusion flags
    excluded_any = 0
    if 'excluded_pregnancy' in df.columns:
        excluded_any = df[
            (df['excluded_pregnancy'] == 1) |
            (df['excluded_kidney_stones'] == 1) |
            (df['excluded_esrd'] == 1) |
            (df['excluded_g6pd'] == 1) |
            (df['excluded_hemochromatosis'] == 1) |
            (df['excluded_early_death'] == 1)
        ].shape[0]

    # Step 7: Save to CSV
    if output:
        df.to_csv(output, index=False)
        if verbose:
            print(f"\n✅ NCT cohort extraction completed in {elapsed:.1f}s")
            print(f"   Output saved to: {output}")
            print(f"\n{'='*80}")
            print(f"NCT COHORT SUMMARY - {treatment_med}")
            print(f"{'='*80}")
            print(f"Total patients:        {total:>6,}")
            if treatment_count > 0 or control_count > 0:
                print(f"Treatment group:       {treatment_count:>6,}  ({treatment_pct:.1f}%)")
                print(f"Control group:         {control_count:>6,}  ({control_pct:.1f}%)")
            if mortality_count > 0:
                print(f"Overall mortality:     {mortality_count:>6,}  ({mortality_pct:.1f}%)")
            if excluded_any > 0:
                print(f"\nNote: {excluded_any} patients had exclusion criteria flags")
            print(f"{'='*80}\n")

            # Additional statistics
            if 'outcome_days' in df.columns:
                print("OUTCOME STATISTICS")
                print(f"{'='*80}")
                print(f"Outcome days (mean ± std):")
                print(f"  Overall:   {df['outcome_days'].mean():.1f} ± {df['outcome_days'].std():.1f}")
                if treatment_count > 0:
                    print(f"  Treatment: {df[df['treatment_group']==1]['outcome_days'].mean():.1f} ± {df[df['treatment_group']==1]['outcome_days'].std():.1f}")
                if control_count > 0:
                    print(f"  Control:   {df[df['treatment_group']==0]['outcome_days'].mean():.1f} ± {df[df['treatment_group']==0]['outcome_days'].std():.1f}")
                print(f"{'='*80}\n")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Execute NCT cohort extraction with dynamic treatment medication"
    )
    parser.add_argument(
        "--sql",
        required=True,
        help="Path to NCT SQL template file (e.g., project/NCT03389555/NCT03389555.sql)"
    )
    parser.add_argument(
        "--treatment-med",
        required=True,
        help="Treatment medication name (e.g., 'hydrocortisone na succ.')"
    )
    parser.add_argument(
        "--output",
        help="Output CSV file path (auto-generated: project/{NCT}/cohorts/{med}/{NCT}_{med}_v{version}.csv)"
    )
    parser.add_argument(
        "--mimic-version",
        default="3.1",
        help="MIMIC-IV version for filename generation (default: 3.1)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )

    args = parser.parse_args()

    # Print header
    if not args.quiet:
        print("\n" + "="*80)
        print("NCT Cohort Extraction (Dynamic Treatment)")
        print("="*80)
        print(f"SQL template: {args.sql}")
        print(f"Treatment medication: {args.treatment_med}")
        print(f"Output file: {args.output}\n")

    try:
        df = run_nct_cohort(
            sql_file=args.sql,
            treatment_med=args.treatment_med,
            output=args.output,
            mimic_version=args.mimic_version,
            verbose=not args.quiet
        )
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
