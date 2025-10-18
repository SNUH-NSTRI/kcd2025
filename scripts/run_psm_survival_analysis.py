#!/usr/bin/env python3
"""
Run PSM + Survival Analysis for NCT Cohorts
Phase 3 → Phase 4: Baseline data → Analysis results

Usage:
    python scripts/run_psm_survival_analysis.py \
        --nct NCT03389555 \
        --treatment-med "hydrocortisone na succ."

Arguments:
    --nct              NCT trial ID (e.g., NCT03389555)
    --treatment-med    Treatment medication name (e.g., "hydrocortisone na succ.")
    --config           Path to baseline_characteristics.yaml (optional)
    --project-root     Project root directory (default: /home/tech/datathon)

Output:
    - Auto-detects input file: project/{NCT}/cohorts/{med_folder}/*_with_baseline.csv
    - Auto-creates output: project/{NCT}/cohorts/{med_folder}/outputs/

Example:
    python scripts/run_psm_survival_analysis.py \
        --nct NCT03389555 \
        --treatment-med "hydrocortisone na succ."

    → Input:  project/NCT03389555/cohorts/hydrocortisonenasucc/NCT03389555_hydrocortisonenasucc_v3.1_with_baseline.csv
    → Output: project/NCT03389555/cohorts/hydrocortisonenasucc/outputs/
"""

import sys
import argparse
from pathlib import Path
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.psm_survival_workflow import PSMSurvivalWorkflow

def normalize_medication_name(med_name):
    """
    Convert medication name to folder name format

    Examples:
        "hydrocortisone na succ." → "hydrocortisonenasucc"
        "Dexamethasone" → "dexamethasone"
        "norepinephrine bitartrate" → "norepinephrinebitartrate"
    """
    # Remove punctuation and convert to lowercase
    normalized = re.sub(r'[^a-z0-9]', '', med_name.lower())
    return normalized

def find_cohort_data(project_root, nct_id, treatment_med):
    """
    Auto-detect cohort data file

    Searches:
        1. project/{NCT}/cohorts/{normalized_med}/
        2. Finds *_with_baseline.csv

    Returns:
        tuple: (cohort_dir, data_file)
    """
    project_dir = Path(project_root) / "project" / nct_id
    cohorts_dir = project_dir / "cohorts"

    if not cohorts_dir.exists():
        raise FileNotFoundError(
            f"Cohorts directory not found: {cohorts_dir}\n"
            f"Expected structure: project/{nct_id}/cohorts/"
        )

    # Normalize medication name
    med_folder = normalize_medication_name(treatment_med)

    # Try to find cohort directory
    cohort_dir = cohorts_dir / med_folder

    if not cohort_dir.exists():
        # Try to find similar directories
        available = [d.name for d in cohorts_dir.iterdir() if d.is_dir()]
        raise FileNotFoundError(
            f"Cohort directory not found: {cohort_dir}\n"
            f"Treatment med: '{treatment_med}' → normalized: '{med_folder}'\n"
            f"Available cohorts: {', '.join(available)}"
        )

    # Find *_with_baseline.csv file
    baseline_files = list(cohort_dir.glob("*_with_baseline.csv"))

    if not baseline_files:
        raise FileNotFoundError(
            f"No baseline data found in: {cohort_dir}\n"
            f"Expected: {nct_id}_{med_folder}_*_with_baseline.csv"
        )

    if len(baseline_files) > 1:
        # Prefer v3.1 version
        v31_files = [f for f in baseline_files if 'v3.1' in f.name]
        if v31_files:
            data_file = v31_files[0]
        else:
            data_file = baseline_files[0]

        print(f"⚠️  Multiple baseline files found, using: {data_file.name}")
    else:
        data_file = baseline_files[0]

    return cohort_dir, data_file

def main():
    parser = argparse.ArgumentParser(
        description='Run PSM + Survival Analysis for NCT Cohorts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--nct',
        required=True,
        help='NCT trial ID (e.g., NCT03389555)'
    )

    parser.add_argument(
        '--treatment-med',
        '--med',
        dest='treatment_med',
        required=True,
        help='Treatment medication name (e.g., "hydrocortisone na succ.")'
    )

    parser.add_argument(
        '--config',
        default=None,
        help='Path to baseline_characteristics.yaml (optional)'
    )

    parser.add_argument(
        '--project-root',
        default='/home/tech/datathon',
        help='Project root directory (default: /home/tech/datathon)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("PSM + SURVIVAL ANALYSIS - NCT COHORT")
    print("=" * 80)
    print()
    print(f"NCT ID: {args.nct}")
    print(f"Treatment: {args.treatment_med}")
    print()

    try:
        # Auto-detect cohort data
        print("🔍 Auto-detecting cohort data...")
        cohort_dir, data_file = find_cohort_data(
            args.project_root,
            args.nct,
            args.treatment_med
        )

        print(f"✓ Found cohort directory: {cohort_dir}")
        print(f"✓ Found baseline data: {data_file.name}")
        print()

        # Set up output directory
        output_dir = cohort_dir / "outputs"
        output_dir.mkdir(exist_ok=True)

        print(f"📁 Output directory: {output_dir}")
        print()

        # Initialize workflow
        print("=" * 80)
        print("INITIALIZING WORKFLOW")
        print("=" * 80)
        print()

        workflow = PSMSurvivalWorkflow(
            project_dir=str(cohort_dir),
            data_csv=data_file.name,
            config_path=args.config
        )

        # Run analysis
        result = workflow.run()

        if result == 0:
            print()
            print("=" * 80)
            print("✅ ANALYSIS COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print(f"Results saved to: {output_dir}")
            print()
            print("Generated files:")
            print("  📊 matched_data_main.csv")
            print("  📊 matched_data_sensitivity.csv")
            print("  📋 baseline_table_main_JAMA.md")
            print("  📈 main_analysis_cumulative_mortality.png")
            print("  📉 main_analysis_smd_plot.png")
            print("  📊 main_survival_summary.csv")
            print("  ... and 16 more files")
            print()
            print("Next steps:")
            print(f"  1. Review {output_dir}/baseline_table_main_JAMA.md")
            print(f"  2. Check {output_dir}/main_analysis_cumulative_mortality.png")
            print(f"  3. See {output_dir}/main_survival_summary.csv for statistics")
        else:
            print()
            print("=" * 80)
            print("❌ ANALYSIS FAILED")
            print("=" * 80)
            return 1

        return 0

    except FileNotFoundError as e:
        print()
        print("=" * 80)
        print("❌ ERROR: File Not Found")
        print("=" * 80)
        print()
        print(str(e))
        print()
        print("Please check:")
        print(f"  1. NCT directory exists: project/{args.nct}/")
        print(f"  2. Cohorts directory exists: project/{args.nct}/cohorts/")
        print(f"  3. Baseline data generated: Run Phase 2→3 first")
        print()
        return 1

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
