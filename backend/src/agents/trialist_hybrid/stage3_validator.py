"""
Stage 3: Deterministic Validation & SQL Generation.

No LLM calls - pure Python logic for reliability and speed.
Implements 4-level validation status and generates executable SQL queries.
"""

import json
from typing import Dict, Any, List, Optional

from agents.trialist_hybrid.models import (
    MappingOutput,
    ValidationResult,
    TemporalConstraint,
)


class Stage3Validator:
    """
    Deterministic validator for Stage 2 mappings.

    Validation Strategy:
    - Schema validation (reuse Stage 2 logic)
    - Confidence thresholds:
      * >= 0.9: passed (no SQL generation issues)
      * 0.7-0.9: warning (SQL generated but needs review)
      * 0.5-0.7: needs_review (no SQL generated)
      * < 0.5: failed (reject)
    - SQL generation using Python templates (not LLM)
    - Edge cases: temporal constraints, unit conversions, negation
    """

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.9
    MEDIUM_CONFIDENCE = 0.7
    LOW_CONFIDENCE = 0.5

    # Known unit conversions
    UNIT_CONVERSIONS = {
        ("Fahrenheit", "Celsius"): lambda f: (f - 32) * 5/9,
        ("lbs", "kg"): lambda lbs: lbs * 0.453592,
        ("inches", "cm"): lambda inches: inches * 2.54,
    }

    def __init__(self, schema_path: str):
        """
        Initialize validator with MIMIC-IV schema.

        Args:
            schema_path: Path to mimic_schema.json
        """
        self.schema = self._load_mimic_schema(schema_path)

    def _load_mimic_schema(self, schema_path: str) -> Dict[str, Any]:
        """Load MIMIC-IV schema from JSON."""
        with open(schema_path, "r") as f:
            return json.load(f)

    def validate(self, mapping_output: MappingOutput) -> ValidationResult:
        """
        Validate mapping and generate SQL query.

        Args:
            mapping_output: Output from Stage 2 mapper

        Returns:
            ValidationResult with status, SQL query, and flags/warnings
        """
        flags: List[str] = []
        warnings: List[str] = []
        confidence = mapping_output.confidence
        criterion = mapping_output.criterion
        mimic_mapping = mapping_output.mimic_mapping

        # Step 1: Schema validation
        if not self._validate_schema(mimic_mapping):
            flags.append("INVALID_SCHEMA")
            return ValidationResult(
                criterion_id=criterion.id,
                validation_status="failed",
                confidence_score=confidence,
                flags=flags,
                warnings=warnings,
                sql_query=None
            )

        # Step 2: Confidence thresholds
        if confidence < self.LOW_CONFIDENCE:
            flags.append("VERY_LOW_CONFIDENCE")
            return ValidationResult(
                criterion_id=criterion.id,
                validation_status="failed",
                confidence_score=confidence,
                flags=flags,
                warnings=warnings,
                sql_query=None
            )

        if confidence < self.MEDIUM_CONFIDENCE:
            warnings.append("LOW_CONFIDENCE")
            return ValidationResult(
                criterion_id=criterion.id,
                validation_status="needs_review",
                confidence_score=confidence,
                flags=flags,
                warnings=warnings,
                sql_query=None
            )

        # Step 3: Additional validation checks
        if not mimic_mapping.sql_condition or not mimic_mapping.sql_condition.strip():
            flags.append("MISSING_SQL_CONDITION")
            return ValidationResult(
                criterion_id=criterion.id,
                validation_status="failed",
                confidence_score=confidence,
                flags=flags,
                warnings=warnings,
                sql_query=None
            )

        # Step 4: Check for unit conversion issues
        unit_warning = self._check_unit_conversions(criterion, mimic_mapping)
        if unit_warning:
            warnings.append(unit_warning)

        # Step 5: Check for complex temporal constraints
        if criterion.temporal_constraint:
            temporal_warning = self._check_temporal_complexity(criterion.temporal_constraint)
            if temporal_warning:
                warnings.append(temporal_warning)

        # Step 6: Add confidence warning if applicable
        if self.MEDIUM_CONFIDENCE <= confidence < self.HIGH_CONFIDENCE:
            warnings.append("MEDIUM_CONFIDENCE")

        # Step 7: Generate SQL query
        try:
            sql_query = self._generate_sql(mapping_output)
        except Exception as e:
            flags.append(f"SQL_GENERATION_ERROR: {str(e)}")
            return ValidationResult(
                criterion_id=criterion.id,
                validation_status="failed",
                confidence_score=confidence,
                flags=flags,
                warnings=warnings,
                sql_query=None
            )

        # Step 8: Determine final status
        if confidence >= self.HIGH_CONFIDENCE and len(warnings) == 0:
            status = "passed"
        elif len(warnings) > 0:
            status = "warning"
        else:
            status = "passed"

        return ValidationResult(
            criterion_id=criterion.id,
            validation_status=status,
            confidence_score=confidence,
            flags=flags,
            warnings=warnings,
            sql_query=sql_query
        )

    def _validate_schema(self, mimic_mapping) -> bool:
        """
        Validate MIMIC-IV schema references.
        Reuses Stage 2 validation logic.
        """
        table = mimic_mapping.table
        if table not in self.schema["tables"]:
            return False

        valid_columns = self.schema["tables"][table]["columns"]
        for col in mimic_mapping.columns:
            if col not in valid_columns:
                return False

        # Check join table if specified
        if mimic_mapping.join_table:
            if mimic_mapping.join_table not in self.schema["tables"]:
                return False
            if mimic_mapping.join_columns:
                join_valid_columns = self.schema["tables"][mimic_mapping.join_table]["columns"]
                for col in mimic_mapping.join_columns:
                    if col not in join_valid_columns:
                        return False

        return True

    def _check_unit_conversions(self, criterion, mimic_mapping) -> Optional[str]:
        """Check if unit conversion is needed and warn."""
        if not criterion.unit:
            return None

        # Temperature units
        if "temperature" in criterion.attribute.lower():
            if "Celsius" in criterion.unit and any(itemid in [223761] for itemid in (mimic_mapping.itemids or [])):
                return "UNIT_MISMATCH: Temperature criterion in Celsius but MIMIC itemid 223761 is Fahrenheit"

        # Weight units (lbs vs kg)
        if "weight" in criterion.attribute.lower():
            if "lbs" in criterion.unit.lower() or "pounds" in criterion.unit.lower():
                return "UNIT_CONVERSION_NEEDED: Weight in lbs, MIMIC typically uses kg"

        return None

    def _check_temporal_complexity(self, temporal: TemporalConstraint) -> Optional[str]:
        """Check for complex temporal logic that may need review."""
        if temporal.operator in ["before", "after"]:
            return "TEMPORAL_COMPLEXITY: before/after operators may require complex SQL joins"

        if temporal.operator == "between":
            return "TEMPORAL_COMPLEXITY: between operator requires range logic"

        return None

    def _generate_sql(self, mapping_output: MappingOutput) -> str:
        """
        Generate SQL query using deterministic Python templates.
        No LLM calls.
        """
        criterion = mapping_output.criterion
        mimic_mapping = mapping_output.mimic_mapping

        # Build SELECT clause
        select_columns = ", ".join(mimic_mapping.columns)

        # Build FROM clause
        from_clause = mimic_mapping.table

        # Build WHERE clause
        where_conditions = []

        # Add itemid filter if present
        if mimic_mapping.itemids:
            itemid_list = ", ".join(str(i) for i in mimic_mapping.itemids)
            where_conditions.append(f"itemid IN ({itemid_list})")

        # Add ICD code filter if present
        if mimic_mapping.icd_codes:
            icd_list = ", ".join(f"'{code}'" for code in mimic_mapping.icd_codes)
            where_conditions.append(f"icd_code IN ({icd_list})")

        # Add main SQL condition
        if mimic_mapping.sql_condition:
            where_conditions.append(mimic_mapping.sql_condition)

        # Add temporal constraint if present
        if criterion.temporal_constraint:
            temporal_sql = self._generate_temporal_sql(criterion.temporal_constraint)
            if temporal_sql:
                where_conditions.append(temporal_sql)

        # Build final WHERE clause
        where_clause = " AND ".join(where_conditions)

        # Build JOIN clause if needed
        join_clause = ""
        if mimic_mapping.join_table:
            join_clause = f"\nJOIN {mimic_mapping.join_table}"
            if mimic_mapping.join_condition:
                join_clause += f" ON {mimic_mapping.join_condition}"

        # Assemble final query
        sql_query = f"""SELECT {select_columns}
FROM {from_clause}{join_clause}
WHERE {where_clause}"""

        return sql_query

    def _generate_temporal_sql(self, temporal: TemporalConstraint) -> Optional[str]:
        """
        Generate SQL for temporal constraints.
        Uses PostgreSQL INTERVAL syntax.
        """
        if temporal.operator == "within_last":
            interval = temporal.to_sql_interval()
            # Assume charttime or admittime as reference
            time_column = "charttime"  # Most common for measurements
            return f"{time_column} >= NOW() - {interval}"

        if temporal.operator == "before":
            # Complex - return None to trigger warning
            return None

        if temporal.operator == "after":
            # Complex - return None to trigger warning
            return None

        return None
