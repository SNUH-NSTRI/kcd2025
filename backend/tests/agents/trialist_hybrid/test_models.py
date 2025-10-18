"""
Unit tests for trialist_hybrid Pydantic models.

Tests cover:
- Valid model instantiation
- Field validation rules
- Edge case handling (negation, temporal, assumptions)
- Invalid input rejection
"""

import pytest
from pydantic import ValidationError

from backend.src.agents.trialist_hybrid.models import (
    CriterionEntity,
    ExtractionOutput,
    MimicMapping,
    MappingOutput,
    PipelineOutput,
    PipelineSummary,
    TemporalConstraint,
    ValidationResult,
)


class TestTemporalConstraint:
    """Test TemporalConstraint model."""

    def test_valid_temporal_constraint(self):
        """Test valid temporal constraint creation."""
        temporal = TemporalConstraint(
            operator="within_last",
            value=6,
            unit="months",
            reference_point="admission"
        )
        assert temporal.operator == "within_last"
        assert temporal.value == 6
        assert temporal.unit == "months"

    def test_to_sql_interval(self):
        """Test SQL interval conversion."""
        temporal = TemporalConstraint(
            operator="within_last",
            value=6,
            unit="months"
        )
        assert temporal.to_sql_interval() == "INTERVAL '6 months'"

    def test_invalid_value_zero(self):
        """Test that value must be greater than 0."""
        with pytest.raises(ValidationError):
            TemporalConstraint(
                operator="within_last",
                value=0,  # Invalid: must be > 0
                unit="months"
            )


class TestCriterionEntity:
    """Test CriterionEntity model."""

    def test_basic_criterion(self):
        """Test basic criterion creation."""
        entity = CriterionEntity(
            id="inc_001",
            text="Age > 18 years",
            entity_type="demographic",
            attribute="age",
            operator=">",
            value="18",
            unit="years"
        )
        assert entity.id == "inc_001"
        assert entity.negation is False
        assert entity.temporal_constraint is None

    def test_criterion_with_negation(self):
        """Test criterion with negation flag."""
        entity = CriterionEntity(
            id="exc_001",
            text="NOT diabetic",
            entity_type="condition",
            attribute="diabetes",
            negation=True
        )
        assert entity.negation is True

    def test_criterion_with_temporal_constraint(self):
        """Test criterion with temporal constraint."""
        entity = CriterionEntity(
            id="inc_002",
            text="Lactate > 2 within 6 months",
            entity_type="measurement",
            attribute="lactate",
            operator=">",
            value="2",
            unit="mmol/L",
            temporal_constraint=TemporalConstraint(
                operator="within_last",
                value=6,
                unit="months"
            )
        )
        assert entity.temporal_constraint is not None
        assert entity.temporal_constraint.value == 6

    def test_criterion_with_assumptions(self):
        """Test criterion with assumptions tracking."""
        entity = CriterionEntity(
            id="inc_003",
            text="Adult patients",
            entity_type="demographic",
            attribute="age",
            operator=">=",
            value="18",
            unit="years",
            assumptions_made=["Assumed 'adult' means age >= 18"]
        )
        assert len(entity.assumptions_made) == 1
        assert "adult" in entity.assumptions_made[0].lower()

    def test_invalid_operator(self):
        """Test that invalid operators are rejected."""
        with pytest.raises(ValidationError):
            CriterionEntity(
                id="inc_001",
                text="Age > 18",
                entity_type="demographic",
                attribute="age",
                operator=">>",  # Invalid operator
                value="18"
            )

    def test_sub_criteria(self):
        """Test complex criterion with sub-criteria."""
        parent = CriterionEntity(
            id="inc_004",
            text="Septic shock (MAP e65 AND Lactate >2)",
            entity_type="condition",
            attribute="septic_shock",
            sub_criteria=[
                CriterionEntity(
                    id="inc_004_a",
                    text="MAP e65",
                    entity_type="measurement",
                    attribute="mean_arterial_pressure",
                    operator=">=",
                    value="65",
                    unit="mmHg"
                ),
                CriterionEntity(
                    id="inc_004_b",
                    text="Lactate >2",
                    entity_type="measurement",
                    attribute="lactate",
                    operator=">",
                    value="2",
                    unit="mmol/L"
                )
            ]
        )
        assert len(parent.sub_criteria) == 2
        assert parent.sub_criteria[0].attribute == "mean_arterial_pressure"


class TestExtractionOutput:
    """Test ExtractionOutput model."""

    def test_empty_extraction(self):
        """Test extraction with no criteria (irrelevant text case)."""
        output = ExtractionOutput()
        assert output.inclusion == []
        assert output.exclusion == []

    def test_extraction_with_criteria(self):
        """Test extraction with inclusion and exclusion criteria."""
        output = ExtractionOutput(
            inclusion=[
                CriterionEntity(
                    id="inc_001",
                    text="Age > 18",
                    entity_type="demographic",
                    attribute="age",
                    operator=">",
                    value="18"
                )
            ],
            exclusion=[
                CriterionEntity(
                    id="exc_001",
                    text="Pregnancy",
                    entity_type="condition",
                    attribute="pregnancy"
                )
            ]
        )
        assert len(output.inclusion) == 1
        assert len(output.exclusion) == 1


class TestMimicMapping:
    """Test MimicMapping model."""

    def test_valid_mimic_mapping(self):
        """Test valid MIMIC-IV mapping."""
        mapping = MimicMapping(
            table="hosp.patients",
            columns=["anchor_age", "anchor_year"],
            join_table="hosp.admissions",
            join_columns=["admittime"],
            join_condition="p.subject_id = a.subject_id",
            sql_condition="anchor_age + EXTRACT(YEAR FROM admittime) - anchor_year > 18"
        )
        assert mapping.table == "hosp.patients"
        assert "anchor_age" in mapping.columns

    def test_invalid_table_format(self):
        """Test that tables without schema.table format are rejected."""
        with pytest.raises(ValidationError):
            MimicMapping(
                table="patients",  # Missing schema prefix
                columns=["anchor_age"],
                sql_condition="anchor_age > 18"
            )

    def test_mapping_with_icd_codes(self):
        """Test mapping with ICD codes for diagnosis."""
        mapping = MimicMapping(
            table="hosp.diagnoses_icd",
            columns=["icd_code", "icd_version"],
            sql_condition="icd_code IN ('I21.0', 'I21.1')",
            icd_codes=["I21.0", "I21.1"]
        )
        assert len(mapping.icd_codes) == 2

    def test_mapping_with_itemids(self):
        """Test mapping with MIMIC itemids for measurements."""
        mapping = MimicMapping(
            table="icu.chartevents",
            columns=["itemid", "valuenum"],
            sql_condition="itemid = 50813 AND valuenum > 2",
            itemids=[50813]  # Lactate
        )
        assert mapping.itemids[0] == 50813


class TestMappingOutput:
    """Test MappingOutput model."""

    def test_valid_mapping_output(self):
        """Test valid mapping output with confidence."""
        output = MappingOutput(
            criterion=CriterionEntity(
                id="inc_001",
                text="Age > 18",
                entity_type="demographic",
                attribute="age",
                operator=">",
                value="18"
            ),
            mimic_mapping=MimicMapping(
                table="hosp.patients",
                columns=["anchor_age"],
                sql_condition="anchor_age > 18"
            ),
            confidence=0.95,
            reasoning="Age is directly stored in patients table"
        )
        assert output.confidence == 0.95

    def test_confidence_rounding(self):
        """Test confidence score is rounded to 2 decimal places."""
        output = MappingOutput(
            criterion=CriterionEntity(
                id="inc_001",
                text="Age > 18",
                entity_type="demographic",
                attribute="age"
            ),
            mimic_mapping=MimicMapping(
                table="hosp.patients",
                columns=["anchor_age"],
                sql_condition="anchor_age > 18"
            ),
            confidence=0.9567,  # Will be rounded
            reasoning="Test"
        )
        assert output.confidence == 0.96

    def test_invalid_confidence_range(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            MappingOutput(
                criterion=CriterionEntity(
                    id="inc_001",
                    text="Age > 18",
                    entity_type="demographic",
                    attribute="age"
                ),
                mimic_mapping=MimicMapping(
                    table="hosp.patients",
                    columns=["anchor_age"],
                    sql_condition="anchor_age > 18"
                ),
                confidence=1.5,  # Invalid: > 1.0
                reasoning="Test"
            )


class TestValidationResult:
    """Test ValidationResult model."""

    def test_passed_validation(self):
        """Test validation result with passed status."""
        result = ValidationResult(
            criterion_id="inc_001",
            validation_status="passed",
            confidence_score=0.95,
            flags=[],
            warnings=[],
            sql_query="SELECT * FROM hosp.patients WHERE anchor_age > 18"
        )
        assert result.validation_status == "passed"
        assert result.sql_query is not None

    def test_failed_validation(self):
        """Test validation result with failed status (no SQL)."""
        result = ValidationResult(
            criterion_id="inc_002",
            validation_status="failed",
            confidence_score=0.3,
            flags=["INVALID_SCHEMA"],
            warnings=[]
        )
        assert result.validation_status == "failed"
        assert result.sql_query is None
        assert "INVALID_SCHEMA" in result.flags

    def test_warning_validation(self):
        """Test validation with warnings."""
        result = ValidationResult(
            criterion_id="inc_003",
            validation_status="warning",
            confidence_score=0.75,
            flags=[],
            warnings=["LOW_CONFIDENCE", "UNIT_CONVERSION"],
            sql_query="SELECT * FROM hosp.patients WHERE anchor_age > 18"
        )
        assert result.validation_status == "warning"
        assert len(result.warnings) == 2


class TestPipelineSummary:
    """Test PipelineSummary model."""

    def test_pipeline_summary(self):
        """Test pipeline summary statistics."""
        summary = PipelineSummary(
            total_criteria=10,
            stage1_extracted=10,
            stage1_extraction_rate=1.0,
            stage2_mapped=9,
            stage2_mapping_rate=0.9,
            stage3_passed=7,
            stage3_warning=2,
            stage3_needs_review=0,
            stage3_failed=0,
            stage3_validation_rate=1.0,
            avg_confidence=0.85,
            execution_time_seconds=25.3
        )
        assert summary.total_criteria == 10
        assert summary.stage3_passed + summary.stage3_warning + summary.stage3_needs_review + summary.stage3_failed == 9


class TestPipelineOutput:
    """Test complete PipelineOutput model."""

    def test_complete_pipeline_output(self):
        """Test complete pipeline output structure."""
        output = PipelineOutput(
            extraction=ExtractionOutput(
                inclusion=[
                    CriterionEntity(
                        id="inc_001",
                        text="Age > 18",
                        entity_type="demographic",
                        attribute="age",
                        operator=">",
                        value="18"
                    )
                ]
            ),
            mappings=[
                MappingOutput(
                    criterion=CriterionEntity(
                        id="inc_001",
                        text="Age > 18",
                        entity_type="demographic",
                        attribute="age",
                        operator=">",
                        value="18"
                    ),
                    mimic_mapping=MimicMapping(
                        table="hosp.patients",
                        columns=["anchor_age"],
                        sql_condition="anchor_age > 18"
                    ),
                    confidence=0.95,
                    reasoning="Direct mapping"
                )
            ],
            validations=[
                ValidationResult(
                    criterion_id="inc_001",
                    validation_status="passed",
                    confidence_score=0.95,
                    sql_query="SELECT * FROM hosp.patients WHERE anchor_age > 18"
                )
            ],
            summary=PipelineSummary(
                total_criteria=1,
                stage1_extracted=1,
                stage1_extraction_rate=1.0,
                stage2_mapped=1,
                stage2_mapping_rate=1.0,
                stage3_passed=1,
                stage3_warning=0,
                stage3_needs_review=0,
                stage3_failed=0,
                stage3_validation_rate=1.0,
                avg_confidence=0.95
            )
        )
        assert len(output.mappings) == 1
        assert output.summary.total_criteria == 1
