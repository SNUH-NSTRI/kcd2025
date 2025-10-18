"""
MIMIC Concept Mapper

Maps OMOP concepts (from Trialist Parser) to MIMIC-IV database tables and ITEMIDs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .trialist_models import EnhancedNamedEntity

logger = logging.getLogger(__name__)


class MimicConceptMapper:
    """
    Maps clinical concepts to MIMIC-IV database structures.

    Provides translation from OMOP concepts (UMLS CUIs) to:
    - MIMIC table names
    - Item IDs (for chartevents, labevents, etc.)
    - ICD codes (for diagnoses)
    - Drug name patterns (for prescriptions)
    """

    def __init__(self, mapping_file: str | Path | None = None):
        """
        Initialize the concept mapper.

        Args:
            mapping_file: Path to JSON mapping file. If None, uses default location.
        """
        if mapping_file is None:
            # Default location: same directory as this module
            mapping_file = Path(__file__).parent / "mimic_concept_mapping.json"

        self.mapping_file = Path(mapping_file)
        self.mappings: Dict[str, Any] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        """Load concept mappings from JSON file."""
        try:
            with open(self.mapping_file, "r", encoding="utf-8") as f:
                self.mappings = json.load(f)
            logger.info(f"Loaded MIMIC concept mappings from {self.mapping_file}")
        except Exception as e:
            logger.error(f"Failed to load MIMIC mappings: {e}")
            # Initialize with empty mappings
            self.mappings = {
                "demographic": {},
                "measurements": {},
                "conditions": {},
                "procedures": {},
                "drugs": {}
            }

    def map_entity(self, entity: EnhancedNamedEntity) -> Dict[str, Any] | None:
        """
        Map a single entity to MIMIC database structures.

        Args:
            entity: Enhanced entity from Trialist Parser

        Returns:
            Mapping dict with table, itemids, and other MIMIC-specific info
        """
        domain = entity.domain.lower()

        # Try to find mapping by UMLS CUI
        if entity.umls_cui:
            mapping = self._lookup_by_cui(entity.umls_cui, domain)
            if mapping:
                return mapping

        # Fallback: Try to find mapping by concept text
        mapping = self._lookup_by_text(entity.text, domain)
        if mapping:
            return mapping

        # No mapping found
        logger.debug(f"No MIMIC mapping found for entity: {entity.text} (domain: {domain}, CUI: {entity.umls_cui})")
        return None

    def _lookup_by_cui(self, cui: str, domain: str) -> Dict[str, Any] | None:
        """Look up mapping by UMLS CUI in specific domain."""
        domain_mappings = self.mappings.get(domain + "s", {})  # e.g., "measurement" -> "measurements"
        if cui in domain_mappings:
            return domain_mappings[cui]
        return None

    def _lookup_by_text(self, text: str, domain: str) -> Dict[str, Any] | None:
        """
        Fallback: Look up mapping by text matching.

        This performs case-insensitive substring matching against concept names.
        """
        domain_mappings = self.mappings.get(domain + "s", {})
        text_lower = text.lower()

        for cui, mapping in domain_mappings.items():
            concept_name = mapping.get("concept_name", "").lower()
            if text_lower in concept_name or concept_name in text_lower:
                logger.info(f"Matched '{text}' to '{mapping.get('concept_name')}' via text similarity")
                return mapping

        return None

    def get_demographic_mapping(self, field_name: str) -> Dict[str, Any] | None:
        """Get mapping for demographic fields (age, gender)."""
        return self.mappings.get("demographic", {}).get(field_name)

    def get_measurement_itemids(self, cui: str) -> List[int] | None:
        """Get MIMIC item IDs for a measurement concept."""
        mapping = self._lookup_by_cui(cui, "measurement")
        if mapping:
            return mapping.get("itemids")
        return None

    def get_condition_icd_codes(self, cui: str) -> tuple[List[str], List[str]] | None:
        """
        Get ICD codes for a condition.

        Returns:
            Tuple of (icd9_codes, icd10_codes) or None if not found
        """
        mapping = self._lookup_by_cui(cui, "condition")
        if mapping:
            icd9 = mapping.get("icd9_codes", [])
            icd10 = mapping.get("icd10_codes", [])
            return (icd9, icd10)
        return None

    def get_drug_name_patterns(self, cui: str) -> List[str] | None:
        """Get drug name patterns for prescription matching."""
        mapping = self._lookup_by_cui(cui, "drug")
        if mapping:
            return mapping.get("drug_name_pattern", [])
        return None

    def get_table_for_domain(self, domain: str) -> str:
        """
        Get the primary MIMIC table for a given domain.

        Args:
            domain: OMOP domain (e.g., "Condition", "Measurement", "Drug")

        Returns:
            MIMIC table name
        """
        domain_table_map = {
            "demographic": "patients",
            "condition": "diagnoses_icd",
            "measurement": "labevents",  # or chartevents
            "procedure": "procedureevents",
            "drug": "prescriptions",
            "observation": "chartevents",
        }
        return domain_table_map.get(domain.lower(), "chartevents")


__all__ = ["MimicConceptMapper"]
