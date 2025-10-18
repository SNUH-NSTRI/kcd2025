"""
Unit tests for Stage 2: MIMIC-IV Mapping.

TDD approach:
- Task 3.1: Basic mapping (Age -> hosp.patients)
- Task 3.3: Invalid table rejection
- Task 3.5: ICD code mapping
- Task 3.7: Temporal SQL generation
"""

import os

import pytest

from backend.src.agents.trialist_hybrid.models import CriterionEntity, MappingOutput
from backend.src.agents.trialist_hybrid.stage2_mapper import Stage2Mapper


@pytest.fixture
def mapper():
    """Create Stage2Mapper instance for testing."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set in environment")

    schema_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "src", "agents", "trialist_hybrid", "prompts", "mimic_schema.json"
    )
    return Stage2Mapper(api_key=api_key, schema_path=schema_path)


class TestBasicMapping:
    """Task 3.1-3.2: Test basic MIMIC-IV mapping."""

    def test_age_to_patients_table(self, mapper):
        """Should map age criterion to hosp.patients table."""
        entity = CriterionEntity(
            id="inc_001",
            text="Age > 18 years",
            entity_type="demographic",
            attribute="age",
            operator=">",
            value="18",
            unit="years"
        )

        result = mapper.map_to_mimic(entity)

        assert isinstance(result, MappingOutput)
        assert result.mimic_mapping.table == "hosp.patients"
        assert "anchor_age" in result.mimic_mapping.columns
        assert result.confidence >= 0.7  # Should be high confidence
        assert "age" in result.reasoning.lower()

    def test_diagnosis_to_diagnoses_icd(self, mapper):
        """Should map diagnosis to hosp.diagnoses_icd table."""
        entity = CriterionEntity(
            id="inc_002",
            text="Septic shock",
            entity_type="condition",
            attribute="septic_shock"
        )

        result = mapper.map_to_mimic(entity)

        assert result.mimic_mapping.table == "hosp.diagnoses_icd"
        assert "icd_code" in result.mimic_mapping.columns
        # Should have ICD codes for septic shock
        assert result.mimic_mapping.icd_codes is not None
        assert len(result.mimic_mapping.icd_codes) > 0

    def test_lab_value_to_labevents(self, mapper):
        """Should map lab value to hosp.labevents with itemid."""
        entity = CriterionEntity(
            id="inc_003",
            text="Lactate > 2 mmol/L",
            entity_type="measurement",
            attribute="lactate",
            operator=">",
            value="2",
            unit="mmol/L"
        )

        result = mapper.map_to_mimic(entity)

        assert result.mimic_mapping.table == "hosp.labevents"
        assert "itemid" in result.mimic_mapping.columns
        assert "valuenum" in result.mimic_mapping.columns
        # Should have lactate itemid (50813)
        assert result.mimic_mapping.itemids is not None
        assert 50813 in result.mimic_mapping.itemids


class TestSchemaValidation:
    """Task 3.3-3.4: Test strict schema validation."""

    def test_valid_table_format(self, mapper):
        """Should accept valid schema.table format."""
        entity = CriterionEntity(
            id="inc_001",
            text="Age > 18",
            entity_type="demographic",
            attribute="age",
            operator=">",
            value="18"
        )

        result = mapper.map_to_mimic(entity)

        # Table name should have schema prefix
        assert "." in result.mimic_mapping.table
        parts = result.mimic_mapping.table.split(".")
        assert len(parts) == 2
        assert parts[0] in ["hosp", "icu"]

    def test_columns_exist_in_schema(self, mapper):
        """Should only use columns that exist in schema."""
        entity = CriterionEntity(
            id="inc_001",
            text="Age > 18",
            entity_type="demographic",
            attribute="age",
            operator=">",
            value="18"
        )

        result = mapper.map_to_mimic(entity)

        # Verify columns against loaded schema
        valid = mapper._validate_against_schema(result)
        assert valid is True, f"Invalid columns in mapping: {result.mimic_mapping.columns}"

    def test_confidence_reduced_on_invalid_schema(self, mapper):
        """Should reduce confidence if schema validation fails."""
        # This test checks the internal validation logic
        # We'll create a mapping with invalid table and check confidence adjustment
        entity = CriterionEntity(
            id="test_001",
            text="Test criterion",
            entity_type="demographic",
            attribute="test_attr"
        )

        result = mapper.map_to_mimic(entity)

        # Even if LLM hallucinates, confidence should reflect uncertainty
        if not mapper._validate_against_schema(result):
            assert result.confidence < 0.7


class TestICDCodeMapping:
    """Task 3.5-3.6: Test ICD code enrichment."""

    def test_sepsis_icd_codes(self, mapper):
        """Should map sepsis to both ICD-9 and ICD-10 codes."""
        entity = CriterionEntity(
            id="inc_001",
            text="Sepsis",
            entity_type="condition",
            attribute="sepsis"
        )

        result = mapper.map_to_mimic(entity)

        assert result.mimic_mapping.icd_codes is not None
        # Should have at least one ICD code
        assert len(result.mimic_mapping.icd_codes) >= 1
        # Check if codes are realistic (ICD-9 or ICD-10 format)
        for code in result.mimic_mapping.icd_codes:
            # ICD-9: 3-5 digits with possible decimal
            # ICD-10: Letter + 2-3 digits
            assert len(code) >= 3

    def test_pregnancy_icd_codes(self, mapper):
        """Should map pregnancy to ICD codes."""
        entity = CriterionEntity(
            id="exc_001",
            text="Pregnancy",
            entity_type="condition",
            attribute="pregnancy"
        )

        result = mapper.map_to_mimic(entity)

        assert result.mimic_mapping.table == "hosp.diagnoses_icd"
        assert result.mimic_mapping.icd_codes is not None
        # Should have pregnancy-related codes
        assert len(result.mimic_mapping.icd_codes) >= 1

    def test_diabetes_icd_codes(self, mapper):
        """Should map diabetes to comprehensive ICD code list."""
        entity = CriterionEntity(
            id="exc_002",
            text="Diabetes mellitus",
            entity_type="condition",
            attribute="diabetes"
        )

        result = mapper.map_to_mimic(entity)

        assert result.mimic_mapping.icd_codes is not None
        # Diabetes has many codes (Type 1, Type 2, complications)
        assert len(result.mimic_mapping.icd_codes) >= 2


class TestTemporalMapping:
    """Task 3.7-3.8: Test temporal constraint SQL generation."""

    def test_within_hours_sql(self, mapper):
        """Should generate SQL for 'within 24 hours' constraint."""
        from backend.src.agents.trialist_hybrid.models import TemporalConstraint

        entity = CriterionEntity(
            id="inc_001",
            text="Septic shock within 24 hours of ICU admission",
            entity_type="condition",
            attribute="septic_shock",
            temporal_constraint=TemporalConstraint(
                operator="within_last",
                value=24,
                unit="hours",
                reference_point="icu_admission"
            )
        )

        result = mapper.map_to_mimic(entity)

        sql = result.mimic_mapping.sql_condition
        # Should contain INTERVAL or time-based filtering
        assert "interval" in sql.lower() or "24" in sql
        # Should reference admission time
        assert "time" in sql.lower()

    def test_before_admission_sql(self, mapper):
        """Should generate SQL for 'before admission' constraint."""
        from backend.src.agents.trialist_hybrid.models import TemporalConstraint

        entity = CriterionEntity(
            id="inc_002",
            text="Antibiotic therapy before admission",
            entity_type="medication",
            attribute="antibiotic",
            temporal_constraint=TemporalConstraint(
                operator="before",
                value=1,
                unit="days",
                reference_point="admission"
            )
        )

        result = mapper.map_to_mimic(entity)

        sql = result.mimic_mapping.sql_condition
        # Should have time comparison
        assert "<" in sql or "before" in sql.lower()


class TestConfidenceScoring:
    """Task 3.9-3.10: Test confidence scoring logic."""

    def test_high_confidence_for_direct_mapping(self, mapper):
        """Should give high confidence for straightforward mappings."""
        entity = CriterionEntity(
            id="inc_001",
            text="Age > 18",
            entity_type="demographic",
            attribute="age",
            operator=">",
            value="18"
        )

        result = mapper.map_to_mimic(entity)

        # Age is a direct mapping -> high confidence
        assert result.confidence >= 0.8

    def test_medium_confidence_for_ambiguous_mapping(self, mapper):
        """Should give medium confidence for ambiguous criteria."""
        entity = CriterionEntity(
            id="inc_002",
            text="Blood pressure abnormal",
            entity_type="measurement",
            attribute="blood_pressure"
        )

        result = mapper.map_to_mimic(entity)

        # Ambiguous (SBP? DBP? MAP?) -> medium confidence
        # Accept 0.5-0.9 range
        assert 0.5 <= result.confidence <= 0.9

    def test_reasoning_explains_confidence(self, mapper):
        """Should provide clear reasoning for confidence score."""
        entity = CriterionEntity(
            id="inc_001",
            text="Lactate > 2",
            entity_type="measurement",
            attribute="lactate",
            operator=">",
            value="2"
        )

        result = mapper.map_to_mimic(entity)

        # Reasoning should be non-empty and meaningful
        assert len(result.reasoning) > 20
        # Should explain the mapping decision
        assert any(
            keyword in result.reasoning.lower()
            for keyword in ["lactate", "itemid", "50813", "lab"]
        )


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_unknown_measurement(self, mapper):
        """Should handle unknown measurement gracefully."""
        entity = CriterionEntity(
            id="inc_001",
            text="Unknown biomarker XYZ-123",
            entity_type="measurement",
            attribute="xyz_123"
        )

        result = mapper.map_to_mimic(entity)

        # Should still return a mapping, but with low confidence
        assert isinstance(result, MappingOutput)
        # Confidence should reflect uncertainty
        assert result.confidence < 0.7

    def test_generic_condition(self, mapper):
        """Should handle generic conditions."""
        entity = CriterionEntity(
            id="exc_001",
            text="Serious illness",
            entity_type="condition",
            attribute="serious_illness"
        )

        result = mapper.map_to_mimic(entity)

        # Should map to diagnoses_icd but with low confidence
        assert result.mimic_mapping.table == "hosp.diagnoses_icd"
        # Confidence reflects ambiguity
        assert result.confidence < 0.8
