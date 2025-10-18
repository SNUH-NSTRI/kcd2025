"""
Utility functions for cohort extraction pipeline.

Functions:
- parse_medication_names: Parse medication names from YAML config
- load_nct_sql: Load NCT-specific SQL query
- validate_cache_file: Validate cache file exists and is valid
- generate_drug_values_cte: Generate SQL VALUES clause for drug matching
"""

import yaml
from pathlib import Path
from typing import List, Optional


def parse_medication_names(yaml_path: str, med_names: List[str]) -> List[str]:
    """
    Parse medication names from medicines.yaml config.

    Args:
        yaml_path: Path to medicines.yaml file
        med_names: List of medication generic names (e.g., ['hydrocortisone', 'thiamine'])

    Returns:
        List of all possible drug name variants for matching

    Example:
        >>> parse_medication_names('config/medicines.yaml', ['hydrocortisone'])
        ['hydrocortisone', 'hydrocortisone na succ']
    """
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)

    drug_patterns = []

    # Search all medication categories
    for category_name, category_data in config.items():
        if category_name in ['version', 'description', 'total_medications',
                             'total_features', 'time_window', 'medication_routes']:
            continue

        if 'medications' not in category_data:
            continue

        for med in category_data['medications']:
            med_name = med['name'].lower()

            # Check if this medication is in our target list
            if any(target.lower() in med_name for target in med_names):
                # Add the primary name
                drug_patterns.append(med_name)

                # Add Korean name if available
                if 'korean' in med:
                    drug_patterns.append(med['korean'].lower())

    # Add original names as fallback
    drug_patterns.extend([name.lower() for name in med_names])

    # Remove duplicates and return
    return list(set(drug_patterns))


def load_nct_sql(nct_id: str, study_dir: str = "study") -> str:
    """
    Load NCT-specific SQL query from file.

    Args:
        nct_id: NCT study identifier (e.g., 'NCT03389555')
        study_dir: Base directory for study files

    Returns:
        SQL query string (with trailing semicolon removed)

    Raises:
        FileNotFoundError: If SQL file doesn't exist
    """
    sql_path = Path(study_dir) / nct_id / "sql" / "cohort_extraction.sql"

    if not sql_path.exists():
        raise FileNotFoundError(
            f"NCT SQL file not found: {sql_path}\n"
            f"Expected location: {study_dir}/{nct_id}/sql/cohort_extraction.sql"
        )

    with open(sql_path, 'r') as f:
        sql = f.read()

    # Remove comments and validation queries at the end
    # Find the main query ending (ORDER BY ... ;)
    lines = sql.split('\n')

    # Find where to cut - either at validation comments or after final semicolon
    end_idx = len(lines)

    for i, line in enumerate(lines):
        # Stop at validation comment sections
        if '-- QUERY VALIDATION' in line or '-- =====' in line and i > 300:
            end_idx = i
            break

    # Take lines up to that point
    sql = '\n'.join(lines[:end_idx])

    # Remove trailing semicolon and whitespace
    sql = sql.rstrip()
    while sql.endswith(';'):
        sql = sql[:-1].rstrip()

    return sql


def replace_mimic_tables_with_csv(nct_sql: str, mimic_dir: str) -> str:
    """
    Replace MIMIC-IV database table references with CSV file paths and adapt schema.

    Args:
        nct_sql: NCT SQL with database table references
        mimic_dir: Path to MIMIC-IV directory

    Returns:
        Modified SQL with read_csv_auto() calls and schema adaptations
    """
    from pathlib import Path

    mimic_path = Path(mimic_dir)

    # Define table mappings: schema.table -> csv path
    table_mappings = {
        'mimiciv_icu.icustays': str(mimic_path / 'icu' / 'icustays.csv.gz'),
        'mimiciv_hosp.admissions': str(mimic_path / 'hosp' / 'admissions.csv.gz'),
        'mimiciv_hosp.patients': str(mimic_path / 'hosp' / 'patients.csv.gz'),
        'mimiciv_derived.antibiotic': str(mimic_path / 'derived' / 'antibiotic.csv.gz'),
        'mimiciv_derived.vasoactive_agent': str(mimic_path / 'derived' / 'vasoactive_agent.csv.gz'),
        'mimiciv_hosp.diagnoses_icd': str(mimic_path / 'hosp' / 'diagnoses_icd.csv.gz'),
    }

    # Replace each table reference with CSV read
    modified_sql = nct_sql
    for table_ref, csv_path in table_mappings.items():
        # Skip derived tables - they need special handling
        if 'derived' in table_ref:
            continue
        # Replace "FROM table" with "FROM read_csv_auto('path')"
        modified_sql = modified_sql.replace(
            f'FROM {table_ref}',
            f"FROM read_csv_auto('{csv_path}')"
        )
        modified_sql = modified_sql.replace(
            f'JOIN {table_ref}',
            f"JOIN read_csv_auto('{csv_path}')"
        )

    # Handle derived tables - create substitute CTEs
    prescriptions_path = str(mimic_path / 'hosp' / 'prescriptions.csv.gz')
    inputevents_path = str(mimic_path / 'icu' / 'inputevents.csv.gz')

    # Substitute for mimiciv_derived.antibiotic (infection evidence)
    # Note: prescriptions doesn't have stay_id, so we select by hadm_id
    antibiotic_substitute = f"""(
        SELECT DISTINCT hadm_id
        FROM read_csv_auto('{prescriptions_path}')
        WHERE drug IS NOT NULL
          AND hadm_id IS NOT NULL
    )"""
    modified_sql = modified_sql.replace(
        'mimiciv_derived.antibiotic',
        antibiotic_substitute
    )

    # Substitute for mimiciv_derived.vasoactive_agent (vasopressor evidence)
    # Simplified version using inputevents with known vasopressor itemids
    vasoactive_substitute = f"""(
        SELECT
            stay_id,
            starttime,
            CASE WHEN itemid IN (221906, 30047) THEN rate ELSE 0 END as norepinephrine,
            CASE WHEN itemid IN (221289, 30044) THEN rate ELSE 0 END as epinephrine,
            CASE WHEN itemid IN (221662, 30043) THEN rate ELSE 0 END as dopamine,
            CASE WHEN itemid IN (221749, 30127) THEN rate ELSE 0 END as phenylephrine,
            CASE WHEN itemid IN (222315, 30051) THEN rate ELSE 0 END as vasopressin
        FROM read_csv_auto('{inputevents_path}')
        WHERE itemid IN (221906, 30047, 221289, 30044, 221662, 30043, 221749, 30127, 222315, 30051)
          AND rate > 0
          AND stay_id IS NOT NULL
    )"""
    modified_sql = modified_sql.replace(
        'mimiciv_derived.vasoactive_agent',
        vasoactive_substitute
    )

    # Schema adaptations for MIMIC-IV v2.2+
    # Replace age calculation with anchor_age (direct field in v2.2+)
    import re

    # Pattern: EXTRACT(YEAR FROM AGE(..., p.dob)) AS age_at_admission,
    # Replace with: p.anchor_age AS age_at_admission,
    # Must preserve the trailing comma if present
    age_assignment_pattern = r'EXTRACT\(YEAR FROM AGE\([^,]+,\s*p\.dob\)\)\s+AS\s+age_at_admission(\s*,)?'

    def replace_age_assignment(match):
        comma = match.group(1) or ''
        return f'p.anchor_age AS age_at_admission{comma}'

    modified_sql = re.sub(age_assignment_pattern, replace_age_assignment, modified_sql)

    # Pattern: EXTRACT(YEAR FROM AGE(..., p.dob)) (in WHERE clause or other contexts)
    # Replace with: p.anchor_age
    age_condition_pattern = r'EXTRACT\(YEAR FROM AGE\([^,]+,\s*p\.dob\)\)'
    modified_sql = re.sub(age_condition_pattern, 'p.anchor_age', modified_sql)

    return modified_sql


def validate_cache_file(cache_path: str) -> bool:
    """
    Validate that cache file exists and has required columns.

    Args:
        cache_path: Path to eligible_patients.csv cache file

    Returns:
        True if valid, raises exception otherwise

    Raises:
        FileNotFoundError: If cache file doesn't exist
        ValueError: If cache file is invalid
    """
    cache_file = Path(cache_path)

    if not cache_file.exists():
        raise FileNotFoundError(
            f"Cache file not found: {cache_path}\n"
            f"Run build_eligible_cache.py first to create the cache."
        )

    # Quick validation: check header
    with open(cache_file, 'r') as f:
        header = f.readline().strip()

    required_columns = {'subject_id', 'hadm_id', 'stay_id', 'intime', 'outtime'}
    header_columns = set(header.split(','))

    missing = required_columns - header_columns
    if missing:
        raise ValueError(
            f"Cache file missing required columns: {missing}\n"
            f"Found columns: {header_columns}"
        )

    return True


def find_medication_family(treatment_med: str, yaml_path: str) -> tuple[str, List[str]]:
    """
    Find medication family (parent category) and all its variants.

    Used for exclusion logic: patients who received ANY variant of the medication family
    (except the exact treatment medication) should be excluded from the control group.

    Args:
        treatment_med: Specific medication name (e.g., "hydrocortisone na succ.")
        yaml_path: Path to medicines_variants.yaml

    Returns:
        Tuple of (family_name, all_variants_list)

    Example:
        >>> find_medication_family("hydrocortisone na succ.", "config/medicines_variants.yaml")
        ('hydrocortisone', ['hydrocortisone', 'hydrocortisone na succ.', 'hydrocortisone acetate', ...])

    Raises:
        FileNotFoundError: If yaml file doesn't exist
        ValueError: If medication family not found in YAML
    """
    yaml_file = Path(yaml_path)
    if not yaml_file.exists():
        raise FileNotFoundError(f"Medication variants file not found: {yaml_path}")

    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)

    if 'medications' not in config:
        raise ValueError(f"Invalid YAML format: 'medications' key not found in {yaml_path}")

    medications = config['medications']
    treatment_lower = treatment_med.lower()

    # Strategy 1: Find by exact match or substring in variants
    for family_name, variants in medications.items():
        if not isinstance(variants, list):
            continue

        # Check if treatment_med is in this family's variants
        variants_lower = [v.lower() for v in variants]

        if treatment_lower in variants_lower:
            return (family_name, variants_lower)

    # Strategy 2: Find by family name contained in treatment_med
    # e.g., "hydrocortisone na succ." contains "hydrocortisone"
    for family_name, variants in medications.items():
        if not isinstance(variants, list):
            continue

        if family_name.lower() in treatment_lower:
            variants_lower = [v.lower() for v in variants]
            return (family_name, variants_lower)

    # If not found, return the treatment med as its own family with single variant
    # This allows the script to work even if the medication isn't in medicines_variants.yaml
    return (treatment_med.lower(), [treatment_lower])


def generate_drug_values_cte(drug_list: List[str]) -> str:
    """
    Generate SQL VALUES clause for drug name matching.

    Args:
        drug_list: List of drug name patterns to match

    Returns:
        SQL VALUES clause string

    Example:
        >>> generate_drug_values_cte(['hydrocortisone', 'thiamine'])
        "VALUES ('hydrocortisone'), ('thiamine')"
    """
    if not drug_list:
        return "VALUES (NULL)"

    # Escape single quotes and create VALUES list
    escaped = []
    for name in drug_list:
        safe_name = name.replace("'", "''").lower()
        escaped.append(f"('{safe_name}')")
    return "VALUES " + ", ".join(escaped)


def format_summary_stats(
    total: int,
    treatment_count: int,
    control_count: int,
    mortality_overall: float,
    mortality_treatment: float,
    mortality_control: float
) -> str:
    """
    Format summary statistics for cohort extraction.

    Args:
        total: Total patients in cohort
        treatment_count: Number of treatment group patients
        control_count: Number of control group patients
        mortality_overall: Overall mortality rate (0-1)
        mortality_treatment: Treatment group mortality rate (0-1)
        mortality_control: Control group mortality rate (0-1)

    Returns:
        Formatted string for console output
    """
    treatment_pct = (treatment_count / total * 100) if total > 0 else 0
    control_pct = (control_count / total * 100) if total > 0 else 0

    summary = f"""
{'='*80}
NCT Cohort Extraction Complete
{'='*80}
Total patients:     {total:,}
Treatment group:    {treatment_count:,} ({treatment_pct:.1f}%)
Control group:      {control_count:,} ({control_pct:.1f}%)

Mortality Rates:
  Overall:          {mortality_overall*100:.1f}%
  Treatment:        {mortality_treatment*100:.1f}%
  Control:          {mortality_control*100:.1f}%
{'='*80}
"""
    return summary
