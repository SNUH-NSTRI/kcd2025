"""
Time Event Ontology (TEO) Mapper for Temporal/Value/Quantity Entities

Maps temporal expressions, quantitative values, and quantity measurements
to Time Event Ontology codes without requiring OHDSI API calls.

This module handles:
- Temporal expressions: "at baseline", "Change from baseline", "3 months"
- Value expressions: "≥ 50%", ">15 mmHg", "< 20 ml/min"
- Quantity expressions: "10mg once daily", "18 years"

TEO Code Structure:
- TEO:BASELINE - Reference time point
- TEO:CHANGE_FROM_BASELINE - Change measurement
- TEO:DURATION - Time duration with ISO 8601 format
- TEO:MEASUREMENT_GTE - Measurement greater than or equal
- TEO:MEASUREMENT_LTE - Measurement less than or equal
- TEO:MEASUREMENT_GT - Measurement greater than
- TEO:MEASUREMENT_LT - Measurement less than
- TEO:MEASUREMENT_EQ - Measurement equals
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .trialist_models import EnhancedNamedEntity

logger = logging.getLogger(__name__)


@dataclass
class TemporalPattern:
    """Temporal pattern definition."""
    patterns: List[str]  # Regex patterns
    teo_code: str  # TEO code
    standard_name: str  # Human-readable name
    metadata: Dict[str, Any] = None


@dataclass
class ValuePattern:
    """Value comparison pattern definition."""
    operator: str  # Comparison operator (≥, ≤, >, <, =)
    operator_code: str  # Operator code (GTE, LTE, GT, LT, EQ)
    standard_name_template: str  # Template for standard name


class TimeEventMapper:
    """
    Maps Temporal/Value/Quantity entities to Time Event Ontology codes.

    This mapper provides offline pattern-based mapping for temporal and
    quantitative expressions that don't require medical vocabulary lookup.

    Usage:
        >>> mapper = TimeEventMapper()
        >>> entity = EnhancedNamedEntity(text="at baseline", domain="Temporal")
        >>> result = mapper.map_entity(entity)
        >>> print(result.primary_code)  # "TEO:BASELINE"

        >>> entity = EnhancedNamedEntity(text="LVEF ≥ 50%", domain="Value")
        >>> result = mapper.map_entity(entity)
        >>> print(result.primary_code)  # "TEO:MEASUREMENT_GTE"
        >>> print(result.metadata["teo_mapping"]["value"])  # 50.0
        >>> print(result.metadata["teo_mapping"]["unit"])  # "percent"
    """

    def __init__(self):
        """Initialize Time Event Mapper with pattern definitions."""
        self.temporal_patterns = self._build_temporal_patterns()
        self.value_operators = self._build_value_operators()
        self.unit_normalizations = self._build_unit_normalizations()
        self.iso_duration_map = self._build_iso_duration_map()

        logger.info("TimeEventMapper initialized")

    def map_entity(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """
        Map a Temporal/Value/Quantity entity to TEO code.

        Args:
            entity: Entity with domain "Temporal", "Value", or "Quantity"

        Returns:
            Enhanced entity with TEO code and metadata

        Raises:
            ValueError: If entity domain is not supported
        """
        if entity.domain == "Temporal":
            return self._map_temporal(entity)
        elif entity.domain == "Value":
            return self._map_value(entity)
        elif entity.domain == "Quantity":
            return self._map_quantity(entity)
        else:
            raise ValueError(
                f"TimeEventMapper only handles Temporal/Value/Quantity domains, "
                f"got: {entity.domain}"
            )

    def _build_temporal_patterns(self) -> Dict[str, TemporalPattern]:
        """Build temporal pattern definitions."""
        return {
            "change_from_baseline": TemporalPattern(
                patterns=[
                    r"\bchange\s+from\s+baseline\b",
                    r"\bfrom\s+baseline\b",
                    r"\bchange\s+over\s+time\b"
                ],
                teo_code="TEO:CHANGE_FROM_BASELINE",
                standard_name="Change from baseline",
                metadata={"temporal_relation": "delta"}
            ),
            "baseline": TemporalPattern(
                patterns=[
                    r"\bat\s+baseline\b",
                    r"\bbaseline$",
                    r"\bat\s+entry\b"
                ],
                teo_code="TEO:BASELINE",
                standard_name="At baseline timepoint",
                metadata={"temporal_relation": "reference_point"}
            ),
            "duration_days": TemporalPattern(
                patterns=[
                    r"(\d+)\s*days?",
                    r"(\d+)\s*d\b"
                ],
                teo_code="TEO:DURATION",
                standard_name="Duration in days",
                metadata={"unit": "days"}
            ),
            "duration_weeks": TemporalPattern(
                patterns=[
                    r"(\d+)\s*weeks?",
                    r"(\d+)\s*wks?",
                    r"(\d+)\s*w\b"
                ],
                teo_code="TEO:DURATION",
                standard_name="Duration in weeks",
                metadata={"unit": "weeks"}
            ),
            "duration_months": TemporalPattern(
                patterns=[
                    r"(\d+)\s*months?",
                    r"(\d+)\s*mos?",
                    r"(\d+)\s*m\b"
                ],
                teo_code="TEO:DURATION",
                standard_name="Duration in months",
                metadata={"unit": "months"}
            ),
            "duration_years": TemporalPattern(
                patterns=[
                    r"(\d+)\s*years?",
                    r"(\d+)\s*yrs?",
                    r"(\d+)\s*y\b"
                ],
                teo_code="TEO:DURATION",
                standard_name="Duration in years",
                metadata={"unit": "years"}
            ),
            "recent": TemporalPattern(
                patterns=[
                    r"\brecent\b",
                    r"\brecently\b"
                ],
                teo_code="TEO:RECENT",
                standard_name="Recent timepoint",
                metadata={"temporal_relation": "relative_past"}
            ),
            "planned": TemporalPattern(
                patterns=[
                    r"\bplanned\b",
                    r"\bfuture\b",
                    r"\bupcoming\b"
                ],
                teo_code="TEO:PLANNED",
                standard_name="Planned timepoint",
                metadata={"temporal_relation": "relative_future"}
            )
        }

    def _build_value_operators(self) -> Dict[str, ValuePattern]:
        """Build value comparison operator definitions."""
        return {
            "≥": ValuePattern(
                operator="≥",
                operator_code="GTE",
                standard_name_template="{measurement} greater than or equal to {value} {unit}"
            ),
            "≤": ValuePattern(
                operator="≤",
                operator_code="LTE",
                standard_name_template="{measurement} less than or equal to {value} {unit}"
            ),
            ">": ValuePattern(
                operator=">",
                operator_code="GT",
                standard_name_template="{measurement} greater than {value} {unit}"
            ),
            "<": ValuePattern(
                operator="<",
                operator_code="LT",
                standard_name_template="{measurement} less than {value} {unit}"
            ),
            "=": ValuePattern(
                operator="=",
                operator_code="EQ",
                standard_name_template="{measurement} equal to {value} {unit}"
            )
        }

    def _build_unit_normalizations(self) -> Dict[str, str]:
        """Build unit normalization mappings."""
        return {
            "%": "percent",
            "mmHg": "millimeters_of_mercury",
            "mmhg": "millimeters_of_mercury",
            "mm Hg": "millimeters_of_mercury",
            "ml/min": "milliliters_per_minute",
            "mL/min": "milliliters_per_minute",
            "years": "years",
            "year": "years",
            "yrs": "years",
            "yr": "years",
            "mg": "milligrams",
            "g": "grams",
            "kg": "kilograms",
            "bpm": "beats_per_minute",
            "°C": "celsius",
            "°F": "fahrenheit"
        }

    def _build_iso_duration_map(self) -> Dict[str, str]:
        """Build ISO 8601 duration format mappings."""
        return {
            "days": "P{}D",
            "weeks": "P{}W",
            "months": "P{}M",
            "years": "P{}Y",
            "hours": "PT{}H",
            "minutes": "PT{}M",
            "seconds": "PT{}S"
        }

    def _map_temporal(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """
        Map temporal entity to TEO code.

        Args:
            entity: Entity with domain "Temporal"

        Returns:
            Enhanced entity with TEO temporal code
        """
        text_lower = entity.text.lower()

        # Try each temporal pattern
        for pattern_name, pattern_def in self.temporal_patterns.items():
            for regex_pattern in pattern_def.patterns:
                match = re.search(regex_pattern, text_lower, re.IGNORECASE)
                if match:
                    # Extract duration value if present
                    duration_value = None
                    iso_duration = None

                    if match.groups():
                        duration_value = int(match.group(1))
                        unit = pattern_def.metadata.get("unit")
                        if unit and unit in self.iso_duration_map:
                            iso_format = self.iso_duration_map[unit]
                            iso_duration = iso_format.format(duration_value)

                    # Build standard name
                    standard_name = pattern_def.standard_name
                    if duration_value:
                        unit_name = pattern_def.metadata.get("unit", "units")
                        standard_name = f"{duration_value} {unit_name}"

                    # Build metadata
                    teo_metadata = {
                        "pattern": pattern_name,
                        "teo_code": pattern_def.teo_code,
                        **pattern_def.metadata
                    }

                    if duration_value:
                        teo_metadata["value"] = duration_value
                        teo_metadata["iso_duration"] = iso_duration

                    return EnhancedNamedEntity(
                        text=entity.text,
                        type=entity.type,
                        domain=entity.domain,
                        start=entity.start,
                        end=entity.end,
                        confidence=0.95,
                        standard_name=standard_name,
                        umls_cui=None,  # TEO doesn't use UMLS CUIs
                        code_system="TEO",
                        code_set=[pattern_def.teo_code],
                        primary_code=pattern_def.teo_code,
                        metadata={
                            **(entity.metadata or {}),
                            "teo_mapping": teo_metadata
                        }
                    )

        # No pattern matched - return with minimal TEO:TEMPORAL
        logger.warning(f"No temporal pattern matched for: {entity.text}")
        return self._create_fallback_temporal(entity)

    def _map_value(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """
        Map value comparison entity to TEO code.

        Args:
            entity: Entity with domain "Value"

        Returns:
            Enhanced entity with TEO value comparison code
        """
        text = entity.text.strip()

        # Regex to extract: [measurement] [operator] [value] [unit]
        # Examples: "LVEF ≥ 50%", ">15 mmHg", "< 20 ml/min"
        value_pattern = r"(.+?)\s*([≥≤><]=?)\s*(\d+(?:\.\d+)?)\s*(%|mmHg|mm Hg|ml/min|mL/min|years?|yrs?|mg|g|kg|bpm)"

        match = re.search(value_pattern, text, re.IGNORECASE)

        if not match:
            # Try pattern without measurement name: "≥ 50%", ">15 mmHg"
            value_pattern_short = r"([≥≤><]=?)\s*(\d+(?:\.\d+)?)\s*(%|mmHg|mm Hg|ml/min|mL/min|years?|yrs?|mg|g|kg|bpm|.*)"
            match = re.search(value_pattern_short, text, re.IGNORECASE)

            if match:
                measurement = ""
                operator = match.group(1)
                value_str = match.group(2)
                unit = match.group(3)
            else:
                logger.warning(f"No value pattern matched for: {text}")
                return self._create_fallback_value(entity)
        else:
            measurement = match.group(1).strip()
            operator = match.group(2)
            value_str = match.group(3)
            unit = match.group(4)

        # Parse value
        try:
            value = float(value_str)
        except ValueError:
            logger.warning(f"Could not parse value from: {value_str}")
            return self._create_fallback_value(entity)

        # Normalize unit
        normalized_unit = self.unit_normalizations.get(unit, unit)

        # Get operator pattern
        operator_pattern = self.value_operators.get(operator)
        if not operator_pattern:
            logger.warning(f"Unknown operator: {operator}")
            return self._create_fallback_value(entity)

        # Build TEO code
        teo_code = f"TEO:MEASUREMENT_{operator_pattern.operator_code}"

        # Build standard name
        if measurement:
            standard_name = operator_pattern.standard_name_template.format(
                measurement=measurement,
                value=value,
                unit=normalized_unit
            )
        else:
            standard_name = f"Value {operator_pattern.operator_code.lower()} {value} {normalized_unit}"

        # Build metadata
        teo_metadata = {
            "operator": operator_pattern.operator_code,
            "operator_symbol": operator,
            "value": value,
            "unit": normalized_unit,
            "unit_original": unit,
            "teo_code": teo_code
        }

        if measurement:
            teo_metadata["measurement"] = measurement

        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=0.95,
            standard_name=standard_name,
            umls_cui=None,
            code_system="TEO",
            code_set=[teo_code],
            primary_code=teo_code,
            metadata={
                **(entity.metadata or {}),
                "teo_mapping": teo_metadata
            }
        )

    def _map_quantity(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """
        Map quantity entity to TEO code.

        Args:
            entity: Entity with domain "Quantity"

        Returns:
            Enhanced entity with TEO quantity code
        """
        # Quantity entities are similar to Value entities but without comparison
        text = entity.text.strip()

        # Extract quantity: [value] [unit]
        quantity_pattern = r"(\d+(?:\.\d+)?)\s*(%|mmHg|ml/min|mL/min|years?|yrs?|mg|g|kg|bpm|.*)"

        match = re.search(quantity_pattern, text, re.IGNORECASE)

        if not match:
            logger.warning(f"No quantity pattern matched for: {text}")
            return self._create_fallback_quantity(entity)

        value_str = match.group(1)
        unit = match.group(2).strip()

        # Parse value
        try:
            value = float(value_str)
        except ValueError:
            logger.warning(f"Could not parse quantity value from: {value_str}")
            return self._create_fallback_quantity(entity)

        # Normalize unit
        normalized_unit = self.unit_normalizations.get(unit, unit)

        # Build TEO code
        teo_code = "TEO:QUANTITY"

        # Build standard name
        standard_name = f"{value} {normalized_unit}"

        # Build metadata
        teo_metadata = {
            "value": value,
            "unit": normalized_unit,
            "unit_original": unit,
            "teo_code": teo_code
        }

        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=0.90,
            standard_name=standard_name,
            umls_cui=None,
            code_system="TEO",
            code_set=[teo_code],
            primary_code=teo_code,
            metadata={
                **(entity.metadata or {}),
                "teo_mapping": teo_metadata
            }
        )

    def _create_fallback_temporal(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """Create fallback TEO entity for unmatched temporal expression."""
        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=0.50,
            standard_name=entity.text,
            umls_cui=None,
            code_system="TEO",
            code_set=["TEO:TEMPORAL"],
            primary_code="TEO:TEMPORAL",
            metadata={
                **(entity.metadata or {}),
                "teo_mapping": {
                    "teo_code": "TEO:TEMPORAL",
                    "note": "Generic temporal entity - no specific pattern matched"
                }
            }
        )

    def _create_fallback_value(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """Create fallback TEO entity for unmatched value expression."""
        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=0.50,
            standard_name=entity.text,
            umls_cui=None,
            code_system="TEO",
            code_set=["TEO:VALUE"],
            primary_code="TEO:VALUE",
            metadata={
                **(entity.metadata or {}),
                "teo_mapping": {
                    "teo_code": "TEO:VALUE",
                    "note": "Generic value entity - no specific pattern matched"
                }
            }
        )

    def _create_fallback_quantity(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """Create fallback TEO entity for unmatched quantity expression."""
        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=0.50,
            standard_name=entity.text,
            umls_cui=None,
            code_system="TEO",
            code_set=["TEO:QUANTITY"],
            primary_code="TEO:QUANTITY",
            metadata={
                **(entity.metadata or {}),
                "teo_mapping": {
                    "teo_code": "TEO:QUANTITY",
                    "note": "Generic quantity entity - no specific pattern matched"
                }
            }
        )


__all__ = ["TimeEventMapper"]
