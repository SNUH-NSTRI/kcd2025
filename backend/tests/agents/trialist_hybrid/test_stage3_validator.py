"""
Unit tests for Stage 3: Deterministic Validation & SQL Generation.

TDD approach:
- Task 4.1-4.2: Basic validation (schema, confidence thresholds)
- Task 4.3-4.4: SQL generation for simple criteria
- Task 4.5-4.6: Temporal SQL and unit conversions
- Task 4.7-4.8: Negation handling and complex criteria
- Task 4.9-4.10: Edge cases and real-world validation
"""

import os
import pytest

from backend.src.agents.trialist_hybrid.models import (
    CriterionEntity,
    MappingOutput,
    MimicMapping,
    TemporalConstraint,
    ValidationResult,
)
from backend.src.agents.trialist_hybrid.stage3_validator import Stage3Validator


@pytest.fixture
def validator():
    """Create Stage3Validator instance for testing."""
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "../../..",
        "src/agents/trialist_hybrid/prompts/mimic_schema.json"
    )
    return Stage3Validator(schema_path=schema_path)


@pytest.fixture
def valid_age_mapping():
    """Valid age > 18 mapping."""
    criterion = CriterionEntity(
        id="inc_001",
        text="Adult patients aged 18 years or older",
        entity_type="demographic",
        attribute="age",
        operator=">=",
        value="18",
        unit="years"
    )
    mapping = MimicMapping(
        table="hosp.patients",
        columns=["subject_id", "anchor_age"],
        sql_condition="anchor_age >= 18"
    )
    return MappingOutput(
        criterion=criterion,
        mimic_mapping=mapping,
        confidence=0.95,
        reasoning="Direct mapping to anchor_age in hosp.patients"
    )


@pytest.fixture
def valid_lactate_mapping():
    """Valid lactate > 2 mmol/L mapping with temporal constraint."""
    criterion = CriterionEntity(
        id="inc_002",
        text="Lactate >2 mmol/L within 24 hours of ICU admission",
        entity_type="measurement",
        attribute="lactate",
        operator=">",
        value="2",
        unit="mmol/L",
        temporal_constraint=TemporalConstraint(
            operator="within_last",
            value=24,
            unit="hours",
            reference_point="icu_admission"
        )
    )
    mapping = MimicMapping(
        table="hosp.labevents",
        columns=["subject_id", "hadm_id", "valuenum", "charttime"],
        itemids=[50813],
        sql_condition="valuenum > 2 AND valueuom = 'mmol/L'"
    )
    return MappingOutput(
        criterion=criterion,
        mimic_mapping=mapping,
        confidence=0.9,
        reasoning="Direct mapping to lactate itemid 50813"
    )


class TestBasicValidation:
    """Task 4.1-4.2: Test basic schema validation and confidence thresholds."""

    def test_high_confidence_passes(self, validator, valid_age_mapping):
        """Should pass validation with high confidence (>=0.9)."""
        result = validator.validate(valid_age_mapping)

        assert isinstance(result, ValidationResult)
        assert result.validation_status == "passed"
        assert result.confidence_score == 0.95
        assert result.sql_query is not None
        assert len(result.flags) == 0
        assert len(result.warnings) == 0

    def test_medium_confidence_warning(self, validator, valid_age_mapping):
        """Should pass with warning for medium confidence (0.7-0.9)."""
        valid_age_mapping.confidence = 0.75
        result = validator.validate(valid_age_mapping)

        assert result.validation_status == "warning"
        assert result.confidence_score == 0.75
        assert result.sql_query is not None
        assert "MEDIUM_CONFIDENCE" in result.warnings

    def test_low_confidence_needs_review(self, validator, valid_age_mapping):
        """Should require review for low confidence (0.5-0.7)."""
        valid_age_mapping.confidence = 0.6
        result = validator.validate(valid_age_mapping)

        assert result.validation_status == "needs_review"
        assert result.confidence_score == 0.6
        assert result.sql_query is None
        assert "LOW_CONFIDENCE" in result.warnings

    def test_very_low_confidence_fails(self, validator, valid_age_mapping):
        """Should fail for very low confidence (<0.5)."""
        valid_age_mapping.confidence = 0.4
        result = validator.validate(valid_age_mapping)

        assert result.validation_status == "failed"
        assert result.confidence_score == 0.4
        assert result.sql_query is None
        assert "VERY_LOW_CONFIDENCE" in result.flags

    def test_invalid_schema_fails(self, validator):
        """Should fail for invalid table reference."""
        criterion = CriterionEntity(
            id="exc_001",
            text="Pregnancy",
            entity_type="condition",
            attribute="pregnancy"
        )
        mapping = MimicMapping(
            table="invalid.table",  # Invalid table
            columns=["subject_id"],
            sql_condition="icd_code IN ('Z33', 'Z34')"
        )
        mapping_output = MappingOutput(
            criterion=criterion,
            mimic_mapping=mapping,
            confidence=0.9,
            reasoning="Invalid table"
        )

        result = validator.validate(mapping_output)

        assert result.validation_status == "failed"
        assert "INVALID_SCHEMA" in result.flags
        assert result.sql_query is None


class TestSQLGeneration:
    """Task 4.3-4.4: Test deterministic SQL generation."""

    def test_simple_numeric_condition(self, validator, valid_age_mapping):
        """Should generate correct SQL for simple numeric condition."""
        result = validator.validate(valid_age_mapping)

        assert result.sql_query is not None
        assert "SELECT" in result.sql_query
        assert "FROM hosp.patients" in result.sql_query
        assert "WHERE anchor_age >= 18" in result.sql_query

    def test_lab_value_with_itemids(self, validator, valid_lactate_mapping):
        """Should generate SQL with itemid filtering."""
        # Remove temporal constraint for this test
        valid_lactate_mapping.criterion.temporal_constraint = None
        result = validator.validate(valid_lactate_mapping)

        assert result.sql_query is not None
        assert "FROM hosp.labevents" in result.sql_query
        assert "itemid IN (50813)" in result.sql_query
        assert "valuenum > 2" in result.sql_query

    def test_icd_code_filtering(self, validator):
        """Should generate SQL with ICD code IN clause."""
        criterion = CriterionEntity(
            id="inc_003",
            text="Sepsis diagnosis",
            entity_type="condition",
            attribute="sepsis"
        )
        mapping = MimicMapping(
            table="hosp.diagnoses_icd",
            columns=["subject_id", "hadm_id", "icd_code"],
            icd_codes=["995.91", "A41.9"],
            sql_condition="icd_code IN ('995.91', 'A41.9')"
        )
        mapping_output = MappingOutput(
            criterion=criterion,
            mimic_mapping=mapping,
            confidence=0.92,
            reasoning="ICD codes for sepsis"
        )

        result = validator.validate(mapping_output)

        assert result.sql_query is not None
        assert "icd_code IN ('995.91', 'A41.9')" in result.sql_query


class TestTemporalSQL:
    """Task 4.5-4.6: Test temporal constraint SQL generation."""

    def test_within_last_temporal(self, validator, valid_lactate_mapping):
        """Should generate SQL for 'within last X hours/days' constraint."""
        result = validator.validate(valid_lactate_mapping)

        assert result.sql_query is not None
        # Should include INTERVAL arithmetic
        assert "INTERVAL '24 hours'" in result.sql_query or "INTERVAL 24" in result.sql_query
        assert "charttime" in result.sql_query

    def test_before_temporal(self, validator):
        """Should generate SQL for 'before' temporal constraint."""
        criterion = CriterionEntity(
            id="exc_002",
            text="MI before admission",
            entity_type="condition",
            attribute="myocardial_infarction",
            temporal_constraint=TemporalConstraint(
                operator="before",
                value=6,
                unit="months",
                reference_point="admission"
            )
        )
        mapping = MimicMapping(
            table="hosp.diagnoses_icd",
            columns=["subject_id", "hadm_id", "icd_code"],
            icd_codes=["410", "I21"],
            sql_condition="icd_code IN ('410', 'I21')"
        )
        mapping_output = MappingOutput(
            criterion=criterion,
            mimic_mapping=mapping,
            confidence=0.85,
            reasoning="MI ICD codes with temporal constraint"
        )

        result = validator.validate(mapping_output)

        assert result.sql_query is not None
        # Should warn about complex temporal logic
        if result.validation_status == "warning":
            assert any("TEMPORAL" in w for w in result.warnings)


class TestUnitConversions:
    """Task 4.5-4.6: Test unit conversion warnings."""

    def test_temperature_conversion_warning(self, validator):
        """Should warn when temperature units differ."""
        criterion = CriterionEntity(
            id="inc_004",
            text="Temperature > 38 degrees C",
            entity_type="measurement",
            attribute="temperature",
            operator=">",
            value="38",
            unit="Celsius"
        )
        mapping = MimicMapping(
            table="icu.chartevents",
            columns=["subject_id", "valuenum", "valueuom"],
            itemids=[223761],  # Temperature Fahrenheit
            sql_condition="valuenum > 38"  # Wrong - needs conversion
        )
        mapping_output = MappingOutput(
            criterion=criterion,
            mimic_mapping=mapping,
            confidence=0.8,
            reasoning="Temperature mapping"
        )

        result = validator.validate(mapping_output)

        # Should warn about unit mismatch
        assert result.validation_status in ["warning", "needs_review"]
        assert any("UNIT" in w for w in result.warnings)


class TestNegationHandling:
    """Task 4.7-4.8: Test negation SQL generation."""

    def test_simple_negation(self, validator):
        """Should generate NOT IN or != for negated criteria."""
        criterion = CriterionEntity(
            id="exc_003",
            text="NOT diabetic",
            entity_type="condition",
            attribute="diabetes",
            negation=True
        )
        mapping = MimicMapping(
            table="hosp.diagnoses_icd",
            columns=["subject_id", "hadm_id", "icd_code"],
            icd_codes=["250", "E10", "E11"],
            sql_condition="icd_code NOT IN ('250', 'E10', 'E11')"
        )
        mapping_output = MappingOutput(
            criterion=criterion,
            mimic_mapping=mapping,
            confidence=0.88,
            reasoning="Negated diabetes diagnosis"
        )

        result = validator.validate(mapping_output)

        assert result.sql_query is not None
        assert "NOT IN" in result.sql_query or "!=" in result.sql_query


class TestComplexCriteria:
    """Task 4.7-4.8: Test complex criteria handling."""

    def test_subcriteria_multiple_mappings(self, validator):
        """Should handle criteria with sub_criteria (AND logic)."""
        # Parent criterion with sub_criteria
        parent = CriterionEntity(
            id="inc_005",
            text="Septic shock (MAP >=65 AND Lactate >2)",
            entity_type="condition",
            attribute="septic_shock",
            sub_criteria=[
                CriterionEntity(
                    id="inc_005_a",
                    text="MAP >=65",
                    entity_type="measurement",
                    attribute="mean_arterial_pressure",
                    operator=">=",
                    value="65",
                    unit="mmHg"
                ),
                CriterionEntity(
                    id="inc_005_b",
                    text="Lactate >2",
                    entity_type="measurement",
                    attribute="lactate",
                    operator=">",
                    value="2",
                    unit="mmol/L"
                )
            ]
        )

        # For parent criteria, might need review
        mapping = MimicMapping(
            table="icu.chartevents",
            columns=["subject_id", "stay_id"],
            sql_condition="Complex AND logic"
        )
        mapping_output = MappingOutput(
            criterion=parent,
            mimic_mapping=mapping,
            confidence=0.7,
            reasoning="Complex criteria with sub_criteria"
        )

        result = validator.validate(mapping_output)

        # Complex criteria should at least not crash
        assert isinstance(result, ValidationResult)
        # May require review due to complexity
        assert result.validation_status in ["passed", "warning", "needs_review"]


class TestEdgeCases:
    """Task 4.9-4.10: Test edge cases and error handling."""

    def test_missing_sql_condition(self, validator):
        """Should fail gracefully for missing sql_condition."""
        criterion = CriterionEntity(
            id="inc_006",
            text="Age > 18",
            entity_type="demographic",
            attribute="age",
            operator=">",
            value="18"
        )
        mapping = MimicMapping(
            table="hosp.patients",
            columns=["subject_id"],
            sql_condition=""  # Empty condition
        )
        mapping_output = MappingOutput(
            criterion=criterion,
            mimic_mapping=mapping,
            confidence=0.9,
            reasoning="Test missing condition"
        )

        result = validator.validate(mapping_output)

        assert result.validation_status in ["failed", "needs_review"]
        assert len(result.flags) > 0 or len(result.warnings) > 0

    def test_null_values_handling(self, validator):
        """Should handle criteria with null optional fields."""
        criterion = CriterionEntity(
            id="exc_004",
            text="Pregnancy",
            entity_type="condition",
            attribute="pregnancy",
            operator=None,  # No operator
            value=None,
            unit=None
        )
        mapping = MimicMapping(
            table="hosp.diagnoses_icd",
            columns=["subject_id", "icd_code"],
            icd_codes=["Z33"],
            sql_condition="icd_code IN ('Z33')"
        )
        mapping_output = MappingOutput(
            criterion=criterion,
            mimic_mapping=mapping,
            confidence=0.91,
            reasoning="Pregnancy diagnosis"
        )

        result = validator.validate(mapping_output)

        # Should handle gracefully
        assert isinstance(result, ValidationResult)
        assert result.sql_query is not None or result.validation_status in ["needs_review", "failed"]


class TestRealWorldCase:
    """Task 4.9-4.10: Test with real NCT03389555 mapping."""

    def test_nct03389555_age_validation(self, validator, valid_age_mapping):
        """Should successfully validate NCT03389555 age criterion."""
        result = validator.validate(valid_age_mapping)

        assert result.validation_status in ["passed", "warning"]
        assert result.sql_query is not None
        assert "anchor_age >= 18" in result.sql_query

    def test_nct03389555_lactate_validation(self, validator, valid_lactate_mapping):
        """Should successfully validate NCT03389555 lactate criterion."""
        result = validator.validate(valid_lactate_mapping)

        assert result.validation_status in ["passed", "warning"]
        assert result.sql_query is not None
        assert "itemid IN (50813)" in result.sql_query or "50813" in result.sql_query
