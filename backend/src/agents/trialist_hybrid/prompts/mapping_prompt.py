"""
Prompt templates for Stage 2: MIMIC-IV Mapping.

Guides LLM to map extracted entities to MIMIC-IV database schema
with strict validation against actual table/column names.
"""

import json

SYSTEM_PROMPT = """You are a MIMIC-IV database expert specializing in mapping clinical trial criteria to the MIMIC-IV schema.

Your task is to map extracted clinical criterion entities to the correct MIMIC-IV tables, columns, and SQL conditions.

CRITICAL REQUIREMENTS:
1. Use ONLY tables and columns that exist in the provided MIMIC-IV schema
2. Generate SQL-ready conditions (WHERE clause format)
3. Map diagnosis criteria to ICD-9/10 codes (use hosp.diagnoses_icd table)
4. Map lab/vital measurements to specific itemids (use hosp.labevents or icu.chartevents)
5. Provide confidence score (0.0-1.0) based on mapping certainty
6. Explain your reasoning clearly

COMMON PATTERNS:

1. AGE CRITERIA:
   - Table: hosp.patients + hosp.admissions (JOIN required)
   - Columns: anchor_age, anchor_year, admittime
   - SQL: anchor_age + EXTRACT(YEAR FROM admittime) - anchor_year > 18
   - Note: anchor_age is age at anchor_year, need to calculate actual age

2. DIAGNOSIS CRITERIA:
   - Table: hosp.diagnoses_icd
   - Columns: icd_code, icd_version
   - SQL: icd_code IN ('995.91', '995.92') AND icd_version = 9
   - Must include: icd_codes array with actual codes
   - Check icd_version (9 or 10)

3. LAB VALUES:
   - Table: hosp.labevents
   - Columns: itemid, valuenum, charttime
   - SQL: itemid = 50813 AND valuenum > 2
   - Must include: itemids array (e.g., [50813] for lactate)
   - Join: hosp.d_labitems for label lookup

4. VITAL SIGNS:
   - Table: icu.chartevents
   - Columns: itemid, valuenum, charttime
   - SQL: itemid IN (220052, 220181) AND valuenum >= 65
   - Must include: itemids array (may have multiple for same measurement)

5. MEDICATIONS:
   - Table: hosp.prescriptions
   - Columns: drug, gsn, ndc, starttime
   - SQL: drug LIKE '%norepinephrine%' OR gsn = '002487'

6. TEMPORAL CONSTRAINTS:
   - Use charttime, admittime, or storetime as reference
   - Within 24 hours: charttime >= admittime - INTERVAL '24 hours'
   - Before admission: charttime < admittime

CONFIDENCE SCORING:
- 0.9-1.0: Direct mapping exists (e.g., age -> anchor_age)
- 0.7-0.9: Clear mapping with minor ambiguity (e.g., MAP has 2 itemids)
- 0.5-0.7: Mapping requires assumptions (e.g., "sepsis" -> specific ICD codes)
- 0.3-0.5: Multiple possible mappings (e.g., "blood pressure" could be SBP/DBP/MAP)
- < 0.3: Unable to map reliably

EXAMPLES:

Input Entity:
{
  "id": "inc_001",
  "text": "Age > 18 years",
  "entity_type": "demographic",
  "attribute": "age",
  "operator": ">",
  "value": "18"
}

Output Mapping:
{
  "criterion": <original entity>,
  "mimic_mapping": {
    "table": "hosp.patients",
    "columns": ["anchor_age", "anchor_year"],
    "join_table": "hosp.admissions",
    "join_columns": ["admittime"],
    "join_condition": "p.subject_id = a.subject_id",
    "sql_condition": "anchor_age + EXTRACT(YEAR FROM a.admittime) - anchor_year > 18"
  },
  "confidence": 0.95,
  "reasoning": "Age is calculated from anchor_age (age at anchor_year) plus years elapsed since anchor_year. Join with admissions required to get admission time."
}

Input Entity:
{
  "id": "inc_002",
  "text": "Lactate > 2 mmol/L",
  "entity_type": "measurement",
  "attribute": "lactate",
  "operator": ">",
  "value": "2",
  "unit": "mmol/L"
}

Output Mapping:
{
  "criterion": <original entity>,
  "mimic_mapping": {
    "table": "hosp.labevents",
    "columns": ["itemid", "valuenum", "valueuom"],
    "sql_condition": "itemid = 50813 AND valuenum > 2",
    "itemids": [50813]
  },
  "confidence": 0.98,
  "reasoning": "Lactate is measured in labevents with itemid 50813. Direct numeric comparison possible."
}

Input Entity:
{
  "id": "inc_003",
  "text": "Septic shock",
  "entity_type": "condition",
  "attribute": "septic_shock"
}

Output Mapping:
{
  "criterion": <original entity>,
  "mimic_mapping": {
    "table": "hosp.diagnoses_icd",
    "columns": ["icd_code", "icd_version"],
    "sql_condition": "icd_code IN ('995.91', '995.92', 'R65.21') AND (icd_version = 9 OR icd_version = 10)",
    "icd_codes": ["995.91", "995.92", "R65.21"]
  },
  "confidence": 0.85,
  "reasoning": "Septic shock maps to ICD-9 codes 995.91/995.92 and ICD-10 code R65.21. Both versions included for completeness."
}
"""


def build_mapping_prompt(entity_json: str, schema_json: str, include_examples: bool = True) -> str:
    """
    Build the mapping prompt for a given criterion entity.

    Args:
        entity_json: JSON string of CriterionEntity
        schema_json: JSON string of MIMIC-IV schema reference
        include_examples: Whether to include real-world examples (default: True)

    Returns:
        Formatted prompt string
    """
    # Load examples if requested
    examples_section = ""
    if include_examples:
        examples_section = load_mapping_examples()
        if examples_section:
            examples_section = f"\n{examples_section}\n"

    return f"""Map the following clinical trial criterion to MIMIC-IV database schema.

CRITERION ENTITY:
{entity_json}

AVAILABLE MIMIC-IV SCHEMA:
{schema_json}
{examples_section}
INSTRUCTIONS:
1. Identify the correct MIMIC-IV table(s) for this criterion
2. Select specific columns needed
3. Generate SQL WHERE clause condition
4. For diagnoses: Include ICD-9/10 codes
5. For measurements: Include itemids
6. For age/temporal: Handle date calculations
7. Estimate confidence score (0.0-1.0)
8. Explain your reasoning

VALIDATION RULES:
- Table names MUST be in schema.table format (e.g., 'hosp.patients')
- Column names MUST exist in the specified table
- Use itemids from common_itemids when available
- Use ICD codes from common_icd_codes when available
- For temporal constraints, use appropriate date arithmetic

OUTPUT FORMAT:
Return a JSON object with this structure:
{{
  "criterion": <original entity object>,
  "mimic_mapping": {{
    "table": "schema.table",
    "columns": ["col1", "col2"],
    "join_table": "schema.join_table" or null,
    "join_columns": ["join_col"] or null,
    "join_condition": "table1.id = table2.id" or null,
    "sql_condition": "WHERE clause condition",
    "icd_codes": ["code1", "code2"] or null,
    "itemids": [12345, 67890] or null
  }},
  "confidence": 0.85,
  "reasoning": "Explanation of mapping decision and any assumptions"
}}

Now map the criterion above.
"""


CORRECTIVE_RETRY_PROMPT = """Your previous mapping attempt had validation errors:

{validation_error}

Common issues:
- Table name not in 'schema.table' format
- Column name doesn't exist in specified table
- Missing required fields (table, columns, sql_condition)
- Confidence not in 0.0-1.0 range

Available schema:
{schema_json}

Original entity:
{entity_json}

Provide the corrected mapping:
"""


def load_mapping_examples(examples_path: str = None, language: str = "ko") -> str:
    """
    Load real-world mapping examples from JSON file.

    Args:
        examples_path: Path to mapping examples JSON (optional)
        language: Language for examples (default: "ko")

    Returns:
        Formatted examples string for prompt injection
    """
    from pathlib import Path

    if examples_path is None:
        # Default to mapping_examples.json in same directory
        examples_path = Path(__file__).parent / "mapping_examples.json"

    try:
        with open(examples_path, "r", encoding="utf-8") as f:
            examples_data = json.load(f)

        if examples_data.get("language") != language:
            # Language mismatch warning (but still proceed)
            pass

        # Format examples for prompt
        formatted = "## Real-World Mapping Examples\n\n"

        # Inclusion criteria examples
        formatted += "### Inclusion Criteria Examples:\n\n"
        for idx, ex in enumerate(examples_data["examples"]["inclusion_criteria"][:5], 1):
            formatted += f"{idx}. **{ex['criterion']}**\n"
            for mapping in ex["mapping"]:
                formatted += f"   >> {mapping}\n"
            formatted += f"   (Category: {ex['category']})\n\n"

        # Exclusion criteria examples
        formatted += "### Exclusion Criteria Examples:\n\n"
        for idx, ex in enumerate(examples_data["examples"]["exclusion_criteria"][:5], 1):
            formatted += f"{idx}. **{ex['criterion']}**\n"
            for mapping in ex["mapping"]:
                formatted += f"   >> {mapping}\n"
            formatted += f"   (Category: {ex['category']})\n\n"

        # Add notes
        formatted += "### Important Notes:\n"
        for note in examples_data.get("notes", []):
            formatted += f"- {note}\n"

        return formatted

    except FileNotFoundError:
        # If examples file not found, return empty string
        return ""
    except Exception as e:
        # Log error but don't fail
        print(f"Warning: Failed to load mapping examples: {e}")
        return ""


def load_schema_with_context(schema_path: str, entity_type: str) -> str:
    """
    Load schema and filter to relevant tables based on entity type.

    Args:
        schema_path: Path to MIMIC schema JSON
        entity_type: Entity type (demographic, condition, measurement, etc.)

    Returns:
        Filtered schema JSON string focusing on relevant tables
    """
    import json
    from pathlib import Path

    with open(schema_path, "r") as f:
        full_schema = json.load(f)

    # Filter schema based on entity type for more focused prompts
    relevant_tables = {
        "demographic": [
            "hosp.patients",
            "hosp.admissions",
        ],
        "condition": [
            "hosp.diagnoses_icd",
            "hosp.d_icd_diagnoses",
        ],
        "procedure": [
            "hosp.procedures_icd",
            "hosp.d_icd_procedures",
        ],
        "measurement": [
            "hosp.labevents",
            "hosp.d_labitems",
            "icu.chartevents",
            "icu.d_items",
        ],
        "medication": [
            "hosp.prescriptions",
        ],
    }

    # Build filtered schema
    filtered_schema = {
        "version": full_schema["version"],
        "tables": {},
        "common_itemids": full_schema.get("common_itemids", {}),
        "common_icd_codes": full_schema.get("common_icd_codes", {}),
    }

    # Add relevant tables
    tables_to_include = relevant_tables.get(entity_type, list(full_schema["tables"].keys()))
    for table_name in tables_to_include:
        if table_name in full_schema["tables"]:
            filtered_schema["tables"][table_name] = full_schema["tables"][table_name]

    return json.dumps(filtered_schema, indent=2)
