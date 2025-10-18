# Scripts Directory

Central scripts for NCT cohort analysis pipeline.

## Available Scripts

### 1. run_nct_cohort.py (Existing - Phase 2→3)
Generates Phase 3 baseline data from Phase 2 cohort data.

```bash
python scripts/run_nct_cohort.py \
    --sql project/NCT03389555/NCT03389555.sql \
    --treatment-med "hydrocortisone na succ." \
    --output project/NCT03389555/cohorts/hydrocortisonenasucc/NCT03389555_hydrocortisonenasucc_v3.1_with_baseline.csv
```

### 2. run_psm_survival_analysis.py (New - Phase 3→4) ⭐

Runs PSM + 28-day survival analysis on Phase 3 baseline data.

**Simple Usage:**
```bash
python scripts/run_psm_survival_analysis.py \
    --nct NCT03389555 \
    --treatment-med "hydrocortisone na succ."
```

**What it does:**
- ✅ Auto-finds input: `project/{NCT}/cohorts/{medication}/*_with_baseline.csv`
- ✅ Auto-creates output: `project/{NCT}/cohorts/{medication}/outputs/`
- ✅ Runs complete PSM + survival analysis
- ✅ Generates 22 output files (tables, figures, data)

**Arguments:**

| Argument | Required | Description | Example |
|:---|:---:|:---|:---|
| `--nct` | ✅ | NCT trial ID | `NCT03389555` |
| `--treatment-med` or `--med` | ✅ | Treatment medication name | `"hydrocortisone na succ."` |
| `--config` | ❌ | Path to baseline config | `config/metadata/baseline_characteristics.yaml` |
| `--project-root` | ❌ | Project root directory | `/home/tech/datathon` |

**Examples:**

```bash
# Basic usage
python scripts/run_psm_survival_analysis.py \
    --nct NCT03389555 \
    --treatment-med "hydrocortisone na succ."

# Short form
python scripts/run_psm_survival_analysis.py \
    --nct NCT03389555 \
    --med "dexamethasone"

# With custom config
python scripts/run_psm_survival_analysis.py \
    --nct NCT03389555 \
    --med "norepinephrine" \
    --config custom/baseline_config.yaml
```

## Pipeline Overview

```
Phase 1: NCT SQL
    ↓
Phase 2: Cohort Extraction (run_nct_cohort.py)
    ↓
Phase 3: Baseline Characteristics (run_nct_cohort.py)
    ↓
Phase 4: PSM + Survival Analysis (run_psm_survival_analysis.py) ⭐
    ↓
Phase 5: Results & Visualization
```

## Directory Structure

```
project/
└── NCT03389555/
    ├── NCT03389555.sql
    └── cohorts/
        ├── hydrocortisonenasucc/
        │   ├── NCT03389555_hydrocortisonenasucc_v3.1.csv              # Phase 2
        │   ├── NCT03389555_hydrocortisonenasucc_v3.1_with_baseline.csv # Phase 3
        │   └── outputs/                                                # Phase 4 ⭐
        │       ├── matched_data_main.csv
        │       ├── baseline_table_main_JAMA.md
        │       ├── main_analysis_cumulative_mortality.png
        │       └── ... (22 files total)
        │
        └── dexamethasone/
            ├── NCT03389555_dexamethasone_v3.1.csv
            ├── NCT03389555_dexamethasone_v3.1_with_baseline.csv
            └── outputs/
                └── ...
```

## Output Files (22 total)

Generated in `project/{NCT}/cohorts/{medication}/outputs/`:

**Data (3):**
- `matched_data_main.csv` - Main analysis matched cohort
- `matched_data_sensitivity.csv` - Sensitivity analysis matched cohort
- `missingness_report.csv` - Data quality report

**Tables (8):**
- `baseline_table_main.csv` - Baseline characteristics (CSV)
- `baseline_table_sensitivity.csv`
- `baseline_table_main_JAMA.md` - JAMA-style Table 1 (full)
- `baseline_table_main_JAMA_simplified.md` - Key variables only
- `baseline_table_sensitivity_JAMA.md`
- `baseline_table_sensitivity_JAMA_simplified.md`
- `smd_main_analysis.csv` - Balance metrics
- `smd_sensitivity_analysis.csv`

**Statistics (2):**
- `main_survival_summary.csv` - Cox model results (HR, CI, p-value)
- `sensitivity_survival_summary.csv`

**Figures (9):**
- `main_analysis_cumulative_mortality.png` - 28-day mortality curve (JAMA style)
- `sensitivity_analysis_cumulative_mortality.png`
- `main_analysis_smd_plot.png` - Balance assessment (Love plot)
- `sensitivity_analysis_smd_plot.png`
- `main_analysis_ps_distribution.png` - Propensity score overlap
- `sensitivity_analysis_ps_distribution.png`
- `main_analysis_km_curve.png` - Kaplan-Meier survival curve
- `sensitivity_analysis_km_curve.png`
- `summary_comparison.png` - Main vs sensitivity comparison

## Medication Name Normalization

The script automatically converts medication names to folder names:

| Input | Folder Name |
|:---|:---|
| `"hydrocortisone na succ."` | `hydrocortisonenasucc` |
| `"Dexamethasone"` | `dexamethasone` |
| `"norepinephrine bitartrate"` | `norepinephrinebitartrate` |

**Rule**: Remove all non-alphanumeric characters and convert to lowercase.

## Troubleshooting

### Error: "Cohorts directory not found"

**Problem**: NCT directory or cohorts subdirectory doesn't exist.

**Solution**:
```bash
# Check structure
ls project/NCT03389555/
ls project/NCT03389555/cohorts/

# Create if needed
mkdir -p project/NCT03389555/cohorts
```

### Error: "No baseline data found"

**Problem**: Phase 3 data not generated yet.

**Solution**: Run Phase 2→3 first:
```bash
python scripts/run_nct_cohort.py \
    --sql project/NCT03389555/NCT03389555.sql \
    --treatment-med "hydrocortisone na succ." \
    --output project/NCT03389555/cohorts/hydrocortisonenasucc/NCT03389555_hydrocortisonenasucc_v3.1_with_baseline.csv
```

### Error: "Variable not in dataset"

**Problem**: CSV missing required baseline variables.

**Solution**: Check `config/metadata/baseline_characteristics.yaml` and ensure CSV has all required columns.

## Batch Processing

Process multiple cohorts:

```bash
# Process all medications for an NCT
for med in "hydrocortisone na succ." "dexamethasone"; do
    python scripts/run_psm_survival_analysis.py \
        --nct NCT03389555 \
        --med "$med"
done

# Process multiple NCTs
for nct in NCT03389555 NCT01234567 NCT99999999; do
    python scripts/run_psm_survival_analysis.py \
        --nct $nct \
        --med "norepinephrine"
done
```

## Dependencies

- Python 3.8+
- poetry
- pandas, numpy, scikit-learn
- lifelines (survival analysis)
- matplotlib, seaborn
- pyyaml

## Related Documentation

- `workflows/README.md` - Workflow module documentation
- `config/metadata/baseline_characteristics.yaml` - Standard variable definitions
- `project/{NCT}/README.md` - NCT-specific documentation

---

**Last Updated**: 2025-10-15
**Version**: 1.0.0
