#!/usr/bin/env python3
"""
Build Eligible Patient Cache for MIMIC-IV Trial Cohort Extraction

Creates a reusable cache of patients who meet basic eligibility criteria:
1. First ICU admission only (per patient)
2. Has ANY medication prescribed within 24 hours of ICU admission

This cache is used as a filter for all subsequent NCT-specific cohort extractions.

Usage:
    python scripts/build_eligible_cache.py \\
        --mimic-dir mimiciv/2.2 \\
        --output outputs/cache/eligible_patients.csv

Output:
    CSV file with columns: subject_id, hadm_id, stay_id, intime, outtime

Performance:
    Expected runtime: < 5 minutes on MIMIC-IV v2.2 (~70K ICU stays)
    Expected cache size: ~40-50K patients

SQL Strategy (Zen-optimized):
    - Uses ROW_NUMBER() with tie-breaker for first admission
    - Uses EXISTS instead of JOIN for 10x faster medication check
    - Adds defensive NULL checks for data quality
"""

import argparse
import duckdb
import time
from pathlib import Path


def build_eligible_cache(mimic_dir: str, output: str, verbose: bool = True) -> dict:
    """
    Build cache of eligible patients from MIMIC-IV database.

    Args:
        mimic_dir: Path to MIMIC-IV directory (e.g., 'mimiciv/2.2')
        output: Output CSV file path
        verbose: Print progress messages

    Returns:
        Dictionary with summary statistics

    Strategy:
        1. Identify first ICU admission per patient using ROW_NUMBER()
        2. Filter for patients with ANY medication within 24h using EXISTS
        3. Save minimal patient keys to CSV for fast reuse
    """
    start_time = time.time()
    mimic_path = Path(mimic_dir)
    icu_dir = mimic_path / "icu"
    hosp_dir = mimic_path / "hosp"

    if verbose:
        print("\n" + "="*80)
        print("🔄 BUILDING ELIGIBLE PATIENT CACHE")
        print("="*80)
        print(f"📁 MIMIC-IV directory: {mimic_dir}")
        print(f"📄 Output file: {output}")
        print("="*80 + "\n")

    # Validate input files
    icustays_file = icu_dir / "icustays.csv.gz"
    prescriptions_file = hosp_dir / "prescriptions.csv.gz"

    if not icustays_file.exists():
        raise FileNotFoundError(f"ICU stays file not found: {icustays_file}")
    if not prescriptions_file.exists():
        raise FileNotFoundError(f"Prescriptions file not found: {prescriptions_file}")

    if verbose:
        print("📊 Step 1/3: Identifying first ICU admission per patient...")
        print("   - Reading ICU stays data")
        print("   - Ranking admissions by time")

    # Connect to DuckDB
    con = duckdb.connect()

    # Zen-optimized SQL query
    sql = f"""
    WITH ranked_stays AS (
        SELECT
            subject_id,
            hadm_id,
            stay_id,
            intime,
            outtime,
            ROW_NUMBER() OVER (
                PARTITION BY subject_id
                ORDER BY intime ASC, stay_id ASC  -- tie-breaker for determinism
            ) as rn
        FROM read_csv_auto('{icustays_file}')
    ),
    first_icu_stays AS (
        SELECT
            subject_id,
            hadm_id,
            stay_id,
            intime,
            outtime
        FROM ranked_stays
        WHERE rn = 1
    ),
    eligible_patients AS (
        SELECT
            icu.subject_id,
            icu.hadm_id,
            icu.stay_id,
            icu.intime,
            icu.outtime
        FROM first_icu_stays icu
        WHERE EXISTS (
            SELECT 1
            FROM read_csv_auto('{prescriptions_file}') p
            WHERE icu.hadm_id = p.hadm_id
              AND p.drug IS NOT NULL
              AND p.starttime >= icu.intime
              AND p.starttime <= (icu.intime + INTERVAL '24 hours')
        )
    )
    SELECT * FROM eligible_patients
    ORDER BY subject_id, hadm_id
    """

    if verbose:
        print("\n💊 Step 2/3: Filtering for 24-hour medication records...")
        print("   - Checking medication prescriptions")
        print("   - Using EXISTS optimization for performance")

    # Execute query
    df = con.execute(sql).df()

    if verbose:
        print("\n💾 Step 3/3: Saving cache to disk...")

    # Create output directory if needed
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    df.to_csv(output, index=False)

    elapsed = time.time() - start_time

    # Calculate statistics
    stats = {
        'total_eligible': len(df),
        'unique_subjects': df['subject_id'].nunique(),
        'unique_admissions': df['hadm_id'].nunique(),
        'execution_time': elapsed,
        'output_file': output
    }

    if verbose:
        print("\n" + "="*80)
        print("✅ CACHE BUILD COMPLETE!")
        print("="*80)
        print(f"📈 Total eligible patients:     {stats['total_eligible']:>7,}")
        print(f"   └─ Unique subjects:          {stats['unique_subjects']:>7,}")
        print(f"   └─ Unique admissions:        {stats['unique_admissions']:>7,}")
        print(f"\n⏱️  Execution time: {elapsed:.1f} seconds")
        print(f"💾 Output saved to: {output}")
        print("="*80)
        print("\n✅ Cache is ready for NCT cohort extraction!\n")

    con.close()
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Build eligible patient cache from MIMIC-IV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python scripts/build_eligible_cache.py

  # Specify MIMIC-IV version
  python scripts/build_eligible_cache.py --mimic-dir mimiciv/3.1

  # Custom output location
  python scripts/build_eligible_cache.py --output data/cache/eligible.csv

Notes:
  - This script should be run ONCE before extracting NCT cohorts
  - Expected runtime: < 5 minutes on MIMIC-IV v2.2
  - Expected cache size: ~40-50K patients (~2-3 MB)
  - Cache includes: subject_id, hadm_id, stay_id, intime, outtime
        """
    )

    parser.add_argument(
        '--mimic-dir',
        default='mimiciv/3.1',
        help='Path to MIMIC-IV directory (default: mimiciv/3.1)'
    )

    parser.add_argument(
        '--output',
        default='cache/eligible_patients_v3.1.csv',
        help='Output CSV file path (default: cache/eligible_patients_v3.1.csv)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )

    args = parser.parse_args()

    try:
        stats = build_eligible_cache(
            mimic_dir=args.mimic_dir,
            output=args.output,
            verbose=not args.quiet
        )

        return 0

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print()
        print("Make sure MIMIC-IV data is extracted to the specified directory:")
        print("  mimiciv/2.2/icu/icustays.csv.gz")
        print("  mimiciv/2.2/hosp/prescriptions.csv.gz")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
