"""
MIMIC-IV Database Schema Reference

This module provides a curated reference of key MIMIC-IV tables and columns
for use in LLM-based clinical concept mapping. It serves as context for
intelligent mapping without requiring external database connections.

Author: Generated for Intelligent MIMIC Mapper
Date: 2025-01-17
"""

from typing import Dict, List, Literal

# Type alias for domain categories
DomainType = Literal["Condition", "Drug", "Measurement", "Procedure", "Observation", "Device"]


# Core MIMIC-IV tables with metadata for LLM context
MIMIC_TABLES: Dict[str, Dict] = {
    "diagnoses_icd": {
        "description": "ICD-9 and ICD-10 diagnosis codes assigned during hospital stay",
        "key_columns": {
            "icd_code": "ICD diagnosis code (e.g., 'A41.9' for sepsis)",
            "icd_version": "ICD version (9 or 10)",
            "seq_num": "Diagnosis priority (1 = primary diagnosis)"
        },
        "domains": ["Condition"],
        "example_filters": [
            "icd_code LIKE 'A41%' -- Sepsis (ICD-10)",
            "icd_code = '78552' -- Septic shock (ICD-9)",
            "icd_version = 10 AND icd_code BETWEEN 'I10' AND 'I15' -- Hypertension"
        ],
        "common_concepts": ["Sepsis", "Pneumonia", "Heart Failure", "COPD", "Diabetes"]
    },

    "labevents": {
        "description": "Laboratory test results from hospital and ICU labs",
        "key_columns": {
            "itemid": "Lab test identifier (links to d_labitems)",
            "value": "Test result as string",
            "valuenum": "Numeric test result (NULL if non-numeric)",
            "valueuom": "Unit of measurement (e.g., 'mg/dL', 'mmol/L')"
        },
        "domains": ["Measurement"],
        "example_filters": [
            "itemid = 50813 AND valuenum > 2.0 -- Lactate > 2.0 mmol/L",
            "itemid = 50912 AND valuenum < 7.35 -- pH < 7.35 (acidosis)",
            "itemid = 51006 -- Blood Urea Nitrogen (BUN)"
        ],
        "common_concepts": ["Lactate", "Creatinine", "Hemoglobin", "Platelet Count", "WBC"],
        "important_itemids": {
            50813: "Lactate",
            50912: "pH",
            50971: "Potassium",
            50983: "Sodium",
            51006: "Blood Urea Nitrogen",
            51221: "Hematocrit",
            51265: "Platelet Count",
            51301: "White Blood Cells"
        }
    },

    "chartevents": {
        "description": "Vital signs and clinical observations from ICU monitoring",
        "key_columns": {
            "itemid": "Chart item identifier (links to d_items)",
            "value": "Observation value as string",
            "valuenum": "Numeric observation value",
            "valueuom": "Unit of measurement"
        },
        "domains": ["Measurement", "Observation"],
        "example_filters": [
            "itemid = 220045 AND valuenum > 100 -- Heart rate > 100 bpm",
            "itemid = 220179 AND valuenum < 90 -- Systolic BP < 90 mmHg",
            "itemid = 223761 AND valuenum > 38.5 -- Temperature > 38.5°C"
        ],
        "common_concepts": ["Heart Rate", "Blood Pressure", "Temperature", "Respiratory Rate", "SpO2"],
        "important_itemids": {
            220045: "Heart Rate",
            220179: "Systolic Blood Pressure",
            220180: "Diastolic Blood Pressure",
            220210: "Respiratory Rate",
            220277: "SpO2",
            223761: "Temperature Celsius",
            223762: "Temperature Fahrenheit"
        }
    },

    "prescriptions": {
        "description": "Medication orders and administration records",
        "key_columns": {
            "drug": "Medication name (free text)",
            "dose_val_rx": "Prescribed dose value",
            "dose_unit_rx": "Dose unit (e.g., 'mg', 'units')",
            "route": "Administration route (e.g., 'IV', 'PO')"
        },
        "domains": ["Drug"],
        "example_filters": [
            "drug ILIKE '%norepinephrine%' -- Vasopressor use",
            "drug ILIKE '%insulin%' -- Insulin therapy",
            "route = 'IV' -- Intravenous medications only"
        ],
        "common_concepts": ["Norepinephrine", "Insulin", "Antibiotics", "Anticoagulants", "Sedatives"]
    },

    "procedures_icd": {
        "description": "ICD-9 and ICD-10 procedure codes performed during hospitalization",
        "key_columns": {
            "icd_code": "ICD procedure code",
            "icd_version": "ICD version (9 or 10)",
            "seq_num": "Procedure priority"
        },
        "domains": ["Procedure"],
        "example_filters": [
            "icd_code = '9604' -- Mechanical ventilation (ICD-9)",
            "icd_code LIKE '5A19%' -- Respiratory ventilation (ICD-10)",
            "icd_version = 10 AND icd_code BETWEEN '02H' AND '02Y' -- Cardiac procedures"
        ],
        "common_concepts": ["Mechanical Ventilation", "Dialysis", "Central Line Insertion", "Intubation"]
    },

    "inputevents": {
        "description": "Fluid and medication inputs administered in ICU (MetaVision)",
        "key_columns": {
            "itemid": "Input item identifier",
            "amount": "Total amount administered",
            "amountuom": "Amount unit of measurement",
            "rate": "Infusion rate",
            "rateuom": "Rate unit"
        },
        "domains": ["Drug", "Observation"],
        "example_filters": [
            "itemid IN (221906, 221289) -- Norepinephrine infusion",
            "itemid = 225158 -- Normal Saline IV",
            "amount > 1000 -- Large volume resuscitation"
        ],
        "common_concepts": ["Vasopressors", "IV Fluids", "Blood Products", "Medications"]
    },

    "outputevents": {
        "description": "Patient output measurements (urine, drains, etc.)",
        "key_columns": {
            "itemid": "Output item identifier",
            "value": "Output volume",
            "valueuom": "Volume unit (typically 'mL')"
        },
        "domains": ["Measurement"],
        "example_filters": [
            "itemid IN (226559, 226560, 226561) -- Urine output",
            "value < 400 -- Oliguria (<400 mL/day)"
        ],
        "common_concepts": ["Urine Output", "Drain Output", "Chest Tube Output"]
    }
}


def get_table_info(table_name: str) -> Dict:
    """
    Get detailed information about a MIMIC-IV table.

    Args:
        table_name: Name of the MIMIC-IV table

    Returns:
        Dictionary with table metadata, or empty dict if table not found

    Example:
        >>> info = get_table_info("labevents")
        >>> print(info["description"])
        Laboratory test results from hospital and ICU labs
    """
    return MIMIC_TABLES.get(table_name, {})


def get_tables_by_domain(domain: DomainType) -> List[str]:
    """
    Get all MIMIC-IV tables that support a specific clinical domain.

    Args:
        domain: Clinical domain (Condition, Drug, Measurement, etc.)

    Returns:
        List of table names that handle the specified domain

    Example:
        >>> tables = get_tables_by_domain("Measurement")
        >>> print(tables)
        ['labevents', 'chartevents', 'outputevents']
    """
    return [
        table_name
        for table_name, metadata in MIMIC_TABLES.items()
        if domain in metadata.get("domains", [])
    ]


def get_all_table_names() -> List[str]:
    """
    Get names of all defined MIMIC-IV tables.

    Returns:
        List of table names

    Example:
        >>> tables = get_all_table_names()
        >>> len(tables)
        7
    """
    return list(MIMIC_TABLES.keys())


def get_schema_summary_for_llm() -> str:
    """
    Generate a concise schema summary formatted for LLM context.

    This function creates a human-readable summary of MIMIC-IV tables
    suitable for inclusion in LLM prompts to guide intelligent mapping.

    Returns:
        Formatted string with table descriptions and key columns

    Example:
        >>> summary = get_schema_summary_for_llm()
        >>> print(summary)
        MIMIC-IV Tables:
        1. diagnoses_icd: ICD-9 and ICD-10 diagnosis codes...
    """
    lines = ["MIMIC-IV Tables:\n"]

    for idx, (table_name, metadata) in enumerate(MIMIC_TABLES.items(), 1):
        lines.append(f"{idx}. {table_name}: {metadata['description']}")
        lines.append(f"   Domains: {', '.join(metadata['domains'])}")
        lines.append(f"   Key Columns: {', '.join(metadata['key_columns'].keys())}")

        # Include example filters for clarity
        if metadata.get("example_filters"):
            lines.append(f"   Example: {metadata['example_filters'][0]}")

        lines.append("")  # Blank line between tables

    return "\n".join(lines)


# Module-level constant for quick LLM prompt injection
MIMIC_SCHEMA_SUMMARY = get_schema_summary_for_llm()


if __name__ == "__main__":
    # Self-test: Print schema summary
    print(MIMIC_SCHEMA_SUMMARY)
    print("\n" + "="*80 + "\n")

    # Test domain lookup
    print("Tables for Measurement domain:")
    print(get_tables_by_domain("Measurement"))

    # Test table info
    print("\nDetails for 'labevents':")
    info = get_table_info("labevents")
    print(f"  Description: {info['description']}")
    print(f"  Common concepts: {', '.join(info['common_concepts'])}")
