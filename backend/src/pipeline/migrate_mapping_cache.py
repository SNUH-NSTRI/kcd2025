"""
Migration Script: Convert old MIMIC concept mapping to new format

This script converts the legacy mimic_concept_mapping.json format
(UMLS CUI-based) to the new IntelligentMimicMapper format
(concept text + domain keys with metadata).

Usage:
    python backend/src/pipeline/migrate_mapping_cache.py

Author: Generated for Intelligent MIMIC Mapper
Date: 2025-01-17
"""

import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_legacy_to_new_format(legacy_file: Path, output_file: Path) -> None:
    """
    Migrate legacy mapping format to new IntelligentMimicMapper format.

    Args:
        legacy_file: Path to old mimic_concept_mapping.json
        output_file: Path to new mapping cache
    """
    # Load legacy mappings
    with open(legacy_file, "r", encoding="utf-8") as f:
        legacy_data = json.load(f)

    new_cache = {}

    # Migrate each domain
    for domain_key, domain_data in legacy_data.items():
        if domain_key.startswith("_"):  # Skip comments
            continue

        # Map legacy domain names to new domain names
        domain_map = {
            "measurements": "Measurement",
            "conditions": "Condition",
            "procedures": "Procedure",
            "drugs": "Drug",
            "demographic": "Demographic"
        }

        domain_name = domain_map.get(domain_key, "Observation")

        # Process each concept in domain
        for cui_or_field, concept_data in domain_data.items():
            concept_name = concept_data.get("concept_name")
            if not concept_name:
                # For demographic fields without concept_name
                concept_name = cui_or_field.replace("_", " ").title()

            # Construct new mapping
            table = concept_data.get("table")
            columns = []
            filter_logic = ""

            # Determine columns and filter logic based on table type
            if table == "diagnoses_icd":
                columns = ["icd_code", "icd_version"]
                icd9 = concept_data.get("icd9_codes", [])
                icd10 = concept_data.get("icd10_codes", [])
                if icd10:
                    filter_logic = f"icd_version = 10 AND icd_code LIKE '{icd10[0]}' -- {concept_name}"
                elif icd9:
                    filter_logic = f"icd_version = 9 AND icd_code LIKE '{icd9[0]}' -- {concept_name}"

            elif table == "labevents":
                columns = ["itemid", "valuenum", "valueuom"]
                itemids = concept_data.get("itemids", [])
                if itemids:
                    filter_logic = f"itemid = {itemids[0]} -- {concept_name}"

            elif table == "chartevents":
                columns = ["itemid", "valuenum"]
                itemids = concept_data.get("itemids", [])
                if itemids:
                    filter_logic = f"itemid IN ({', '.join(map(str, itemids))}) -- {concept_name}"

            elif table == "prescriptions":
                columns = ["drug"]
                drug_patterns = concept_data.get("drug_name_pattern", [])
                if drug_patterns:
                    filter_logic = f"drug ILIKE '%{drug_patterns[0]}%' -- {concept_name}"

            elif table == "procedures_icd":
                columns = ["icd_code", "icd_version"]
                icd9 = concept_data.get("icd9_codes", [])
                icd10 = concept_data.get("icd10_codes", [])
                if icd10:
                    filter_logic = f"icd_version = 10 AND icd_code LIKE '{icd10[0]}' -- {concept_name}"
                elif icd9:
                    filter_logic = f"icd_version = 9 AND icd_code LIKE '{icd9[0]}' -- {concept_name}"

            elif table == "patients":
                columns = [concept_data.get("column", "value")]
                filter_logic = f"-- Demographic field: {concept_name}"

            # Create normalized key
            concept_key = f"{concept_name.lower().replace(' ', '_')}_{domain_name.lower()}"

            # Build new mapping entry
            new_cache[concept_key] = {
                "mapping": {
                    "table": table or "chartevents",
                    "columns": columns or ["value"],
                    "filter_logic": filter_logic or f"-- Manual mapping required for {concept_name}"
                },
                "confidence": 1.0,  # Legacy mappings are manually verified
                "reasoning": f"Migrated from legacy CUI {cui_or_field}",
                "alternatives": [],
                "source": "manual",
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"Migrated: {concept_name} ({domain_name}) -> {concept_key}")

    # Save new cache
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(new_cache, f, indent=2, ensure_ascii=False)

    logger.info(f"✓ Migration complete: {len(new_cache)} concepts migrated")
    logger.info(f"✓ New cache saved to: {output_file}")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    legacy_file = script_dir / "mimic_concept_mapping.json"
    new_file = script_dir / "mimic_concept_mapping_v2.json"

    if not legacy_file.exists():
        logger.error(f"Legacy file not found: {legacy_file}")
        exit(1)

    migrate_legacy_to_new_format(legacy_file, new_file)

    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS:")
    logger.info("1. Review new cache: backend/src/pipeline/mimic_concept_mapping_v2.json")
    logger.info("2. Test with IntelligentMimicMapper")
    logger.info("3. If satisfied, replace old cache:")
    logger.info("   mv mimic_concept_mapping.json mimic_concept_mapping_legacy.json")
    logger.info("   mv mimic_concept_mapping_v2.json mimic_concept_mapping.json")
