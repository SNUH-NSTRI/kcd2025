"""
Pattern Matching Library for Clinical Trial Criteria.

This module implements pattern recognition for common clinical trial eligibility
criteria and generates corresponding OMOP CDM SQL queries for cohort filtering.

Supported Patterns:
- AgeRangePattern: Age >= X AND Age <= Y
- DrugExclusionPattern: NOT EXISTS drug_exposure WHERE drug_concept_id IN (...)
- TemporalExclusionPattern: condition_start_date < enrollment_date - interval 'X months'
- MeasurementThresholdPattern: measurement_value > X AND measurement_unit = 'Y'

Usage:
    matcher = PatternMatcher()
    patterns = matcher.detect_patterns(entities)
    sql_queries = [p.to_sql() for p in patterns]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, Literal
from abc import ABC, abstractmethod

from .trialist_models import EnhancedNamedEntity


class ClinicalPattern(Protocol):
    """Protocol for clinical trial eligibility patterns."""

    def match(self, entities: Sequence[EnhancedNamedEntity]) -> bool:
        """
        Detect if this pattern matches the given entities.

        Args:
            entities: Sequence of enhanced named entities to analyze

        Returns:
            True if pattern is detected, False otherwise
        """
        ...

    def to_sql(self) -> str:
        """
        Generate OMOP CDM SQL query for this pattern.

        Returns:
            SQL query string for cohort filtering
        """
        ...


@dataclass
class AgeRangePattern:
    """
    Pattern: Age within a range (age >= X AND age <= Y).

    Example:
        "Age >= 18 years and <= 65 years"

    SQL Template:
        SELECT person_id FROM person
        WHERE EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_datetime)) >= {min_age}
          AND EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_datetime)) <= {max_age}
    """

    min_age: float | None = None
    max_age: float | None = None
    operator_min: str | None = None  # >=, >
    operator_max: str | None = None  # <=, <

    def match(self, entities: Sequence[EnhancedNamedEntity]) -> bool:
        """Detect age range pattern from entities."""
        age_entities = [
            e for e in entities
            if e.domain == "Demographic"
            and "age" in e.text.lower()
        ]

        if len(age_entities) < 1:
            return False

        # Check for single entity with range
        has_range = any(e.value_range is not None for e in age_entities)
        if has_range:
            entity = next(e for e in age_entities if e.value_range is not None)
            self.min_age = entity.value_range[0]
            self.max_age = entity.value_range[1]
            self.operator_min = ">="
            self.operator_max = "<="
            return True

        # Check for entities with numeric values and operators
        age_value_entities = [
            e for e in age_entities
            if e.numeric_value is not None
        ]

        if len(age_value_entities) >= 2:
            # Find min and max from operators
            for entity in age_value_entities:
                if entity.operator in (">", ">="):
                    self.min_age = entity.numeric_value
                    self.operator_min = entity.operator
                elif entity.operator in ("<", "<="):
                    self.max_age = entity.numeric_value
                    self.operator_max = entity.operator
            return self.min_age is not None or self.max_age is not None
        elif len(age_value_entities) == 1:
            # Single age constraint (e.g., age >= 18)
            entity = age_value_entities[0]
            if entity.operator in (">", ">="):
                self.min_age = entity.numeric_value
                self.operator_min = entity.operator
                return True
            elif entity.operator in ("<", "<="):
                self.max_age = entity.numeric_value
                self.operator_max = entity.operator
                return True

        return False

    def to_sql(self) -> str:
        """Generate OMOP CDM SQL for age range filtering."""
        conditions = []

        if self.min_age is not None:
            op = self.operator_min or ">="
            conditions.append(
                f"EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_datetime)) {op} {self.min_age}"
            )

        if self.max_age is not None:
            op = self.operator_max or "<="
            conditions.append(
                f"EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_datetime)) {op} {self.max_age}"
            )

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        return f"""SELECT person_id FROM person
WHERE {where_clause}"""


@dataclass
class DrugExclusionPattern:
    """
    Pattern: Exclude patients with specific drug exposure.

    Example:
        "No use of anticoagulants within 30 days"

    SQL Template:
        SELECT person_id FROM person
        WHERE person_id NOT IN (
            SELECT person_id FROM drug_exposure
            WHERE drug_concept_id IN ({concept_ids})
            AND drug_exposure_start_date >= CURRENT_DATE - INTERVAL '{days} days'
        )
    """

    drug_concept_ids: Sequence[str] | None = None
    drug_names: Sequence[str] | None = None
    temporal_constraint: str | None = None  # ISO 8601 duration (P30D)
    reference_point: str | None = None  # enrollment, admission, etc.

    def match(self, entities: Sequence[EnhancedNamedEntity]) -> bool:
        """Detect drug exclusion pattern from entities."""
        # Find negation cue
        has_negation = any(e.domain == "Negation_cue" for e in entities)

        # Find drug entities
        drug_entities = [e for e in entities if e.domain == "Drug"]

        # Find temporal constraint
        temporal_entities = [
            e for e in entities
            if e.domain == "Temporal" and e.iso_duration is not None
        ]

        if not has_negation or not drug_entities:
            return False

        # Extract drug information
        self.drug_names = [e.text for e in drug_entities]
        self.drug_concept_ids = [
            code for e in drug_entities if e.code_set for code in e.code_set
        ]

        # Extract temporal constraint
        if temporal_entities:
            self.temporal_constraint = temporal_entities[0].iso_duration
            self.reference_point = temporal_entities[0].reference_point

        return True

    def to_sql(self) -> str:
        """Generate OMOP CDM SQL for drug exclusion filtering."""
        concept_ids_str = ", ".join(self.drug_concept_ids) if self.drug_concept_ids else "'UNKNOWN'"

        # Convert ISO 8601 duration to SQL interval
        interval_str = "INTERVAL '30 days'"
        if self.temporal_constraint:
            # P30D -> 30 days, P3M -> 3 months, P1Y -> 1 year
            duration = self.temporal_constraint
            if duration.startswith("P") and "D" in duration:
                days = duration.replace("P", "").replace("D", "")
                interval_str = f"INTERVAL '{days} days'"
            elif duration.startswith("P") and "M" in duration:
                months = duration.replace("P", "").replace("M", "")
                interval_str = f"INTERVAL '{months} months'"
            elif duration.startswith("P") and "Y" in duration:
                years = duration.replace("P", "").replace("Y", "")
                interval_str = f"INTERVAL '{years} years'"

        return f"""SELECT person_id FROM person
WHERE person_id NOT IN (
    SELECT person_id FROM drug_exposure
    WHERE drug_concept_id IN ({concept_ids_str})
    AND drug_exposure_start_date >= CURRENT_DATE - {interval_str}
)"""


@dataclass
class TemporalExclusionPattern:
    """
    Pattern: Exclude conditions occurring before/after a reference point.

    Example:
        "No myocardial infarction within 3 months before enrollment"

    SQL Template:
        SELECT person_id FROM person
        WHERE person_id NOT IN (
            SELECT person_id FROM condition_occurrence
            WHERE condition_concept_id IN ({concept_ids})
            AND condition_start_date >= enrollment_date - INTERVAL '3 months'
        )
    """

    condition_concept_ids: Sequence[str] | None = None
    condition_names: Sequence[str] | None = None
    temporal_constraint: str | None = None  # ISO 8601 duration
    temporal_pattern: str | None = None  # XBeforeY, XWithinTime, etc.
    reference_point: str | None = None

    def match(self, entities: Sequence[EnhancedNamedEntity]) -> bool:
        """Detect temporal exclusion pattern from entities."""
        has_negation = any(e.domain == "Negation_cue" for e in entities)
        condition_entities = [e for e in entities if e.domain == "Condition"]
        temporal_entities = [
            e for e in entities
            if e.domain == "Temporal"
            and (e.iso_duration is not None or e.temporal_pattern is not None)
        ]

        if not has_negation or not condition_entities or not temporal_entities:
            return False

        # Extract condition information
        self.condition_names = [e.text for e in condition_entities]
        self.condition_concept_ids = [
            code for e in condition_entities if e.code_set for code in e.code_set
        ]

        # Extract temporal information
        temp_entity = temporal_entities[0]
        self.temporal_constraint = temp_entity.iso_duration
        self.temporal_pattern = temp_entity.temporal_pattern
        self.reference_point = temp_entity.reference_point or "enrollment"

        return True

    def to_sql(self) -> str:
        """Generate OMOP CDM SQL for temporal exclusion filtering."""
        concept_ids_str = ", ".join(self.condition_concept_ids) if self.condition_concept_ids else "'UNKNOWN'"

        # Convert ISO 8601 to SQL interval
        interval_str = "INTERVAL '3 months'"
        if self.temporal_constraint:
            duration = self.temporal_constraint
            if duration.startswith("P") and "D" in duration:
                days = duration.replace("P", "").replace("D", "")
                interval_str = f"INTERVAL '{days} days'"
            elif duration.startswith("P") and "M" in duration:
                months = duration.replace("P", "").replace("M", "")
                interval_str = f"INTERVAL '{months} months'"
            elif duration.startswith("P") and "Y" in duration:
                years = duration.replace("P", "").replace("Y", "")
                interval_str = f"INTERVAL '{years} years'"

        reference_date = f"{self.reference_point}_date" if self.reference_point else "enrollment_date"

        return f"""SELECT person_id FROM person
WHERE person_id NOT IN (
    SELECT co.person_id FROM condition_occurrence co
    JOIN cohort c ON co.person_id = c.subject_id
    WHERE co.condition_concept_id IN ({concept_ids_str})
    AND co.condition_start_date >= c.{reference_date} - {interval_str}
)"""


@dataclass
class MeasurementThresholdPattern:
    """
    Pattern: Measurement value meets threshold criteria.

    Example:
        "HbA1c > 7.0%" or "eGFR >= 60 mL/min/1.73m²"

    SQL Template:
        SELECT person_id FROM measurement
        WHERE measurement_concept_id IN ({concept_ids})
          AND value_as_number {operator} {threshold}
          AND unit_concept_id = {unit_concept_id}
    """

    measurement_concept_ids: Sequence[str] | None = None
    measurement_names: Sequence[str] | None = None
    operator: str | None = None  # >, <, >=, <=, =
    threshold: float | None = None
    unit: str | None = None
    ucum_unit: str | None = None

    def match(self, entities: Sequence[EnhancedNamedEntity]) -> bool:
        """Detect measurement threshold pattern from entities."""
        measurement_entities = [
            e for e in entities
            if e.domain == "Measurement"
            and e.numeric_value is not None
            and e.operator is not None
        ]

        if not measurement_entities:
            return False

        # Extract measurement information from first entity
        entity = measurement_entities[0]
        self.measurement_names = [entity.text]
        self.measurement_concept_ids = list(entity.code_set) if entity.code_set else None
        self.operator = entity.operator
        self.threshold = entity.numeric_value
        self.unit = entity.unit
        self.ucum_unit = entity.ucum_unit

        return True

    def to_sql(self) -> str:
        """Generate OMOP CDM SQL for measurement threshold filtering."""
        concept_ids_str = ", ".join(self.measurement_concept_ids) if self.measurement_concept_ids else "'UNKNOWN'"
        operator = self.operator or ">"
        threshold = self.threshold or 0
        unit_constraint = f"AND unit_source_value = '{self.unit}'" if self.unit else ""

        return f"""SELECT DISTINCT person_id FROM measurement
WHERE measurement_concept_id IN ({concept_ids_str})
  AND value_as_number {operator} {threshold}
  {unit_constraint}"""


class PatternMatcher:
    """
    Orchestrator for detecting and applying clinical trial eligibility patterns.

    This class coordinates pattern detection across multiple pattern types and
    provides utility methods for pattern analysis and SQL generation.
    """

    def __init__(self):
        """Initialize pattern matcher with all available pattern types."""
        self.pattern_classes = [
            AgeRangePattern,
            DrugExclusionPattern,
            TemporalExclusionPattern,
            MeasurementThresholdPattern,
        ]

    def detect_patterns(
        self, entities: Sequence[EnhancedNamedEntity]
    ) -> list[ClinicalPattern]:
        """
        Detect all applicable patterns from entity sequence.

        Args:
            entities: Sequence of enhanced named entities from trial criteria

        Returns:
            List of detected pattern instances
        """
        detected_patterns = []

        for pattern_class in self.pattern_classes:
            pattern = pattern_class()
            if pattern.match(entities):
                detected_patterns.append(pattern)

        return detected_patterns

    def generate_sql_queries(
        self, entities: Sequence[EnhancedNamedEntity]
    ) -> list[str]:
        """
        Generate SQL queries for all detected patterns.

        Args:
            entities: Sequence of enhanced named entities

        Returns:
            List of SQL query strings
        """
        patterns = self.detect_patterns(entities)
        return [pattern.to_sql() for pattern in patterns]

    def analyze_patterns(
        self, entities: Sequence[EnhancedNamedEntity]
    ) -> dict[str, list[str]]:
        """
        Analyze entity sequence and return pattern statistics.

        Args:
            entities: Sequence of enhanced named entities

        Returns:
            Dictionary with pattern types and their detected instances
        """
        patterns = self.detect_patterns(entities)
        analysis = {}

        for pattern in patterns:
            pattern_type = type(pattern).__name__
            if pattern_type not in analysis:
                analysis[pattern_type] = []
            analysis[pattern_type].append(str(pattern))

        return analysis
