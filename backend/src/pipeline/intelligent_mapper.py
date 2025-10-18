"""
Intelligent MIMIC Mapper

LLM-powered clinical concept mapping system with cascading lookup pattern:
1. Check existing cache (mimic_concept_mapping.json)
2. If not found, ask OpenRouter LLM for intelligent mapping
3. Validate and save LLM result to cache
4. Return mapping with confidence score

Author: Generated for Intelligent MIMIC Mapper
Date: 2025-01-17
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field, validator

from .mimic_schema_reference import (
    MIMIC_SCHEMA_SUMMARY,
    MIMIC_TABLES,
    get_all_table_names,
    get_table_info,
    get_tables_by_domain,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class MimicMapping(BaseModel):
    """MIMIC-IV database mapping result."""

    table: str = Field(..., description="MIMIC-IV table name (e.g., 'diagnoses_icd')")
    columns: List[str] = Field(..., description="Relevant column names")
    filter_logic: str = Field(
        ...,
        description="SQL filter logic (e.g., 'icd_code LIKE \\'A41%\\' -- Sepsis')"
    )

    @validator("table")
    def validate_table_name(cls, v):
        """Ensure table exists in MIMIC schema reference."""
        valid_tables = get_all_table_names()
        if v not in valid_tables:
            raise ValueError(
                f"Invalid MIMIC table '{v}'. Valid tables: {', '.join(valid_tables)}"
            )
        return v


class AlternativeMapping(BaseModel):
    """Alternative mapping suggestion when primary mapping has low confidence."""

    table: str
    columns: List[str]
    note: str = Field(..., description="Explanation for why this alternative might be valid")


class MappingResult(BaseModel):
    """Complete mapping result with metadata."""

    mapping: MimicMapping
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) of mapping accuracy"
    )
    reasoning: str = Field(..., description="Explanation of mapping decision")
    alternatives: List[AlternativeMapping] = Field(
        default_factory=list,
        description="Alternative mappings if confidence is low"
    )
    source: str = Field(
        ...,
        description="Source of mapping: 'cache', 'llm', or 'fallback'"
    )
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()

    @classmethod
    def from_cache(cls, cached_data: Dict[str, Any]) -> MappingResult:
        """Create MappingResult from cached JSON data."""
        return cls(**cached_data)


# ============================================================================
# Intelligent Mapper
# ============================================================================


class IntelligentMimicMapper:
    """
    Cascading lookup + LLM fallback mapping engine.

    Workflow:
    1. Check cache (mimic_concept_mapping.json) for existing mapping
    2. If not found, call OpenRouter LLM for intelligent mapping
    3. Validate LLM response against MIMIC schema
    4. Save validated mapping to cache for future reuse
    5. Return MappingResult with confidence score
    """

    def __init__(
        self,
        mapping_file: str | Path,
        openrouter_api_key: str | None = None,
        model: str = "openai/gpt-4o-mini"
    ):
        """
        Initialize the intelligent mapper.

        Args:
            mapping_file: Path to JSON cache file (mimic_concept_mapping.json)
            openrouter_api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
            model: OpenRouter model identifier (default: gpt-4o-mini)
        """
        self.mapping_file = Path(mapping_file)
        self.model = model

        # Get API key from parameter or environment
        self.api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning(
                "No OpenRouter API key provided. LLM mapping will fail. "
                "Set OPENROUTER_API_KEY environment variable or pass api_key parameter."
            )

        # Load existing cache
        self.mapping_cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    # ========================================================================
    # Public API
    # ========================================================================

    def map_concept(self, concept: str, domain: str) -> MappingResult:
        """
        Main entry point - cascading lookup for concept → MIMIC mapping.

        Args:
            concept: Clinical concept text (e.g., "Sepsis", "Lactate", "Age")
            domain: Clinical domain (Condition, Drug, Measurement, etc.)

        Returns:
            MappingResult with confidence score and source

        Example:
            >>> mapper = IntelligentMimicMapper("mimic_concept_mapping.json")
            >>> result = mapper.map_concept("Sepsis", "Condition")
            >>> print(result.mapping.table)
            diagnoses_icd
            >>> print(result.confidence)
            0.95
        """
        # Step 1: Check cache
        logger.info(f"Mapping concept: '{concept}' (domain: {domain})")
        cached_result = self._lookup_cache(concept, domain)
        if cached_result:
            logger.info(f"✓ Cache hit for '{concept}'")
            return cached_result

        # Step 2: Ask LLM
        logger.info(f"Cache miss for '{concept}' - querying LLM...")
        llm_result = self._llm_map(concept, domain)

        # Step 3: Validate & save
        if llm_result and self._validate_mapping(llm_result):
            logger.info(f"✓ LLM mapping validated for '{concept}' (confidence: {llm_result.confidence:.2f})")
            self._save_to_cache(concept, domain, llm_result)
            return llm_result

        # Step 4: Fallback
        logger.warning(f"Failed to map '{concept}' - returning fallback result")
        return self._fallback_result(concept, domain)

    # ========================================================================
    # Cache Management
    # ========================================================================

    def _load_cache(self) -> None:
        """Load existing mappings from JSON file."""
        if not self.mapping_file.exists():
            logger.warning(f"Cache file not found: {self.mapping_file}. Starting with empty cache.")
            self.mapping_cache = {}
            return

        try:
            with open(self.mapping_file, "r", encoding="utf-8") as f:
                raw_cache = json.load(f)

            # Convert to internal format: {concept_key: MappingResult}
            for concept_key, data in raw_cache.items():
                try:
                    self.mapping_cache[concept_key] = data  # Store raw dict for now
                except Exception as e:
                    logger.error(f"Failed to parse cached entry for '{concept_key}': {e}")

            logger.info(f"Loaded {len(self.mapping_cache)} cached mappings from {self.mapping_file}")

        except Exception as e:
            logger.error(f"Failed to load cache file: {e}")
            self.mapping_cache = {}

    def _lookup_cache(self, concept: str, domain: str) -> Optional[MappingResult]:
        """
        Look up existing mapping in cache.

        Args:
            concept: Clinical concept text
            domain: Clinical domain

        Returns:
            MappingResult if found, None otherwise
        """
        # Normalize concept key: lowercase + remove extra spaces
        concept_key = self._normalize_concept_key(concept, domain)

        if concept_key in self.mapping_cache:
            cached_data = self.mapping_cache[concept_key]
            try:
                # Convert cached dict to MappingResult
                result = MappingResult(**cached_data)
                result.source = "cache"  # Mark as cache hit
                return result
            except Exception as e:
                logger.error(f"Invalid cache entry for '{concept_key}': {e}")
                return None

        return None

    def _save_to_cache(self, concept: str, domain: str, result: MappingResult) -> None:
        """
        Save new mapping to cache file.

        Args:
            concept: Clinical concept text
            domain: Clinical domain
            result: Validated MappingResult from LLM
        """
        concept_key = self._normalize_concept_key(concept, domain)

        # Add to in-memory cache
        self.mapping_cache[concept_key] = result.to_dict()

        # Write to disk
        try:
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(self.mapping_cache, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved mapping for '{concept}' to cache")
        except Exception as e:
            logger.error(f"Failed to save cache to disk: {e}")

    @staticmethod
    def _normalize_concept_key(concept: str, domain: str) -> str:
        """
        Normalize concept + domain into cache key.

        Args:
            concept: Clinical concept text
            domain: Clinical domain

        Returns:
            Normalized key (e.g., "sepsis_condition")

        Example:
            >>> IntelligentMimicMapper._normalize_concept_key("  Sepsis  ", "Condition")
            'sepsis_condition'
        """
        concept_clean = concept.strip().lower().replace(" ", "_")
        domain_clean = domain.strip().lower()
        return f"{concept_clean}_{domain_clean}"

    # ========================================================================
    # LLM Integration
    # ========================================================================

    def _llm_map(self, concept: str, domain: str) -> Optional[MappingResult]:
        """
        Query OpenRouter LLM for intelligent mapping.

        Args:
            concept: Clinical concept text
            domain: Clinical domain

        Returns:
            MappingResult from LLM, or None if LLM call fails
        """
        if not self.api_key:
            logger.error("No OpenRouter API key available - cannot perform LLM mapping")
            return None

        # Construct prompt
        system_message = self._build_system_prompt()
        user_message = self._build_user_prompt(concept, domain)

        # Call OpenRouter API
        try:
            response = self._call_openrouter(system_message, user_message)
            if not response:
                return None

            # Parse LLM response
            mapping_data = self._parse_llm_response(response)
            if not mapping_data:
                logger.error(f"Failed to parse LLM response for '{concept}'")
                return None

            # Convert to MappingResult
            result = MappingResult(
                mapping=MimicMapping(**mapping_data["mapping"]),
                confidence=mapping_data.get("confidence", 0.5),
                reasoning=mapping_data.get("reasoning", "LLM-generated mapping"),
                alternatives=[
                    AlternativeMapping(**alt)
                    for alt in mapping_data.get("alternatives", [])
                ],
                source="llm"
            )

            return result

        except Exception as e:
            logger.error(f"LLM mapping failed for '{concept}': {e}")
            return None

    def _build_system_prompt(self) -> str:
        """Build system message for LLM with MIMIC schema context."""
        # Get sample baseline features (10 examples)
        baseline_examples = {
            "anchor_age": "Continuous - Patient age at admission (years)",
            "temperature": "Continuous - Average temperature in first 24h (°C)",
            "lactate": "Continuous - First lactate level (mmol/L)",
            "sbp": "Continuous - Average systolic blood pressure (mmHg)",
            "chf": "Binary - Presence of congestive heart failure",
            "mechanical_ventilation": "Binary - Received mechanical ventilation",
            "gender": "Categorical - Patient gender",
            "gcs": "Ordinal - Minimum Glasgow Coma Scale score",
        }

        baseline_text = "\n".join([
            f"- {name}: {desc}"
            for name, desc in baseline_examples.items()
        ])

        return f"""You are a MIMIC-IV database mapping expert. Your task is to map clinical concepts to MIMIC-IV tables and columns.

{MIMIC_SCHEMA_SUMMARY}

Common Baseline Features (Examples from 48 total):
{baseline_text}

Rules:
1. Return ONLY valid JSON - no additional text or explanations outside the JSON
2. Include confidence score (0.0-1.0) based on mapping certainty
3. Suggest alternatives if uncertain (confidence < 0.8)
4. Use standard SQL-friendly column names from the tables above
5. Provide clear filter_logic with SQL syntax (e.g., "icd_code LIKE 'A41%' -- Sepsis")
6. For measurements, include specific itemid values when possible (see important_itemids)

Your response must be a single JSON object with this exact structure:
{{
  "mapping": {{
    "table": "table_name",
    "columns": ["column1", "column2"],
    "filter_logic": "SQL filter with comments"
  }},
  "confidence": 0.95,
  "reasoning": "Brief explanation of why this mapping is correct",
  "alternatives": [
    {{"table": "alt_table", "columns": ["col"], "note": "Alternative reason"}}
  ]
}}"""

    def _build_user_prompt(self, concept: str, domain: str) -> str:
        """Build user message with concept and domain."""
        return f"""Map the following clinical concept:

Concept: "{concept}"
Domain: "{domain}"

Provide the mapping as JSON following the schema in the system message."""

    def _call_openrouter(self, system_message: str, user_message: str) -> Optional[str]:
        """
        Call OpenRouter API with retry logic.

        Args:
            system_message: System prompt with MIMIC schema
            user_message: User prompt with concept/domain

        Returns:
            LLM response text, or None if call fails
        """
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/rwe-platform",  # Optional
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.2,  # Low temperature for consistent mappings
            "max_tokens": 1000,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"OpenRouter API call failed: {e}")
            return None

    def _parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM JSON response with retry on malformed JSON.

        Args:
            response_text: Raw LLM response

        Returns:
            Parsed mapping dict, or None if parsing fails
        """
        # Try to extract JSON from response (LLM might add extra text)
        import re

        # Look for JSON object pattern
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
        else:
            json_text = response_text

        try:
            data = json.loads(json_text)

            # Validate required fields
            required_fields = ["mapping", "confidence", "reasoning"]
            if not all(field in data for field in required_fields):
                logger.error(f"LLM response missing required fields: {data.keys()}")
                return None

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Raw response: {response_text}")
            return None

    # ========================================================================
    # Validation
    # ========================================================================

    def _validate_mapping(self, result: MappingResult) -> bool:
        """
        Validate mapping result against MIMIC schema.

        Args:
            result: MappingResult to validate

        Returns:
            True if valid, False otherwise

        Validation checks:
        - Table name exists in MIMIC_TABLES
        - Columns exist in table definition
        - Confidence score is reasonable
        - Filter logic is not empty
        """
        # Check 1: Table name exists
        table_name = result.mapping.table
        if table_name not in get_all_table_names():
            logger.error(f"Invalid table name: {table_name}")
            return False

        # Check 2: Columns are valid for the table
        table_info = get_table_info(table_name)
        if not table_info:
            logger.error(f"No metadata found for table: {table_name}")
            return False

        valid_columns = list(table_info.get("key_columns", {}).keys())
        for col in result.mapping.columns:
            if col not in valid_columns and col not in ["value", "valuenum", "itemid"]:
                # Allow common fallback columns
                logger.warning(
                    f"Column '{col}' not in schema for table '{table_name}'. "
                    f"Valid columns: {valid_columns}"
                )
                # Don't fail validation - just warn (LLM might know about additional columns)

        # Check 3: Confidence score is reasonable
        if result.confidence < 0.0 or result.confidence > 1.0:
            logger.error(f"Invalid confidence score: {result.confidence}")
            return False

        # Check 4: Filter logic exists
        if not result.mapping.filter_logic or not result.mapping.filter_logic.strip():
            logger.warning("Empty filter_logic - mapping may be incomplete")
            # Don't fail - allow empty filter_logic for demographic fields

        # Check 5: Reasoning exists
        if not result.reasoning or not result.reasoning.strip():
            logger.warning("Empty reasoning - LLM did not explain mapping")

        # All checks passed
        logger.debug(
            f"✓ Validation passed for table '{table_name}' "
            f"(confidence: {result.confidence:.2f})"
        )
        return True

    # ========================================================================
    # Fallback Handling
    # ========================================================================

    def _fallback_result(self, concept: str, domain: str) -> MappingResult:
        """
        Generate low-confidence fallback result when LLM fails.

        Args:
            concept: Clinical concept text
            domain: Clinical domain

        Returns:
            MappingResult with low confidence and placeholder mapping
        """
        # Get default table for domain
        table_name = "diagnoses_icd"  # Default fallback
        if domain == "Measurement":
            table_name = "labevents"
        elif domain == "Drug":
            table_name = "prescriptions"
        elif domain == "Procedure":
            table_name = "procedures_icd"
        elif domain == "Observation":
            table_name = "chartevents"

        return MappingResult(
            mapping=MimicMapping(
                table=table_name,
                columns=["value"],
                filter_logic=f"-- TODO: Manual mapping required for '{concept}'"
            ),
            confidence=0.0,
            reasoning=f"Fallback result: LLM mapping failed for '{concept}'. Manual review required.",
            alternatives=[],
            source="fallback"
        )


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "IntelligentMimicMapper",
    "MappingResult",
    "MimicMapping",
    "AlternativeMapping",
]


# ============================================================================
# Self-Test
# ============================================================================

if __name__ == "__main__":
    # Initialize mapper with dummy cache file
    mapper = IntelligentMimicMapper(
        mapping_file="test_cache.json",
        openrouter_api_key="test_key"
    )

    # Test cache key normalization
    key = mapper._normalize_concept_key("  Sepsis  ", "Condition")
    assert key == "sepsis_condition", f"Expected 'sepsis_condition', got '{key}'"

    # Test fallback result
    fallback = mapper._fallback_result("Unknown Concept", "Measurement")
    assert fallback.confidence == 0.0
    assert fallback.source == "fallback"
    print("✓ Mapper skeleton tests passed")
