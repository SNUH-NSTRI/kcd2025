"""
Unit tests for Stage 1: Structured Extraction.

TDD approach:
- Task 2.1: Basic extraction (Age > 18)
- Task 2.3: Negation handling
- Task 2.5: Temporal constraints
- Task 2.7: Complex criteria (AND/OR)
"""

import os

import pytest
from pydantic import ValidationError

from backend.src.agents.trialist_hybrid.models import CriterionEntity, ExtractionOutput
from backend.src.agents.trialist_hybrid.stage1_extractor import Stage1Extractor


@pytest.fixture
def extractor():
    """Create Stage1Extractor instance for testing."""
    # Check if OPENROUTER_API_KEY is available
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set in environment")
    return Stage1Extractor(api_key=api_key)


@pytest.fixture
def nct03389555_criteria():
    """Load NCT03389555 real criteria."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "nct03389555_criteria.txt"
    )
    with open(fixture_path, "r") as f:
        return f.read()


class TestBasicExtraction:
    """Task 2.1-2.2: Test basic criterion extraction."""

    def test_simple_age_criterion(self, extractor):
        """Should extract basic age criterion correctly."""
        criteria = "Inclusion: Age > 18 years"

        result = extractor.extract(criteria)

        assert isinstance(result, ExtractionOutput)
        assert len(result.inclusion) == 1
        assert len(result.exclusion) == 0

        entity = result.inclusion[0]
        assert entity.entity_type == "demographic"
        assert entity.attribute == "age"
        assert entity.operator == ">"
        assert entity.value == "18"
        assert entity.unit == "years"
        assert entity.negation is False

    def test_multiple_inclusion_criteria(self, extractor):
        """Should extract multiple inclusion criteria."""
        criteria = """
        Inclusion:
        - Age >= 18 years
        - Diagnosed with septic shock
        """

        result = extractor.extract(criteria)

        assert len(result.inclusion) >= 2
        # At least age and diagnosis
        entity_types = [e.entity_type for e in result.inclusion]
        assert "demographic" in entity_types
        assert "condition" in entity_types

    def test_both_inclusion_and_exclusion(self, extractor):
        """Should separate inclusion and exclusion criteria."""
        criteria = """
        Inclusion: Age >= 18 years
        Exclusion: Pregnancy
        """

        result = extractor.extract(criteria)

        assert len(result.inclusion) >= 1
        assert len(result.exclusion) >= 1
        assert result.inclusion[0].entity_type == "demographic"
        assert result.exclusion[0].entity_type == "condition"


class TestNegationHandling:
    """Task 2.3-2.4: Test negation detection."""

    def test_explicit_not_keyword(self, extractor):
        """Should detect NOT keyword and set negation flag."""
        criteria = "Exclusion: NOT diabetic"

        result = extractor.extract(criteria)

        assert len(result.exclusion) >= 1
        entity = result.exclusion[0]
        assert entity.negation is True
        assert "diabet" in entity.attribute.lower()

    def test_exclude_prefix(self, extractor):
        """Should detect 'exclude' as negation indicator."""
        criteria = "Exclude patients with pregnancy"

        result = extractor.extract(criteria)

        # Should be in exclusion OR have negation=True
        if len(result.exclusion) > 0:
            assert result.exclusion[0].entity_type == "condition"
        elif len(result.inclusion) > 0:
            assert result.inclusion[0].negation is True

    def test_no_history_phrase(self, extractor):
        """Should detect 'no history of' as negation."""
        criteria = "Inclusion: No history of heart failure"

        result = extractor.extract(criteria)

        assert len(result.inclusion) >= 1
        entity = result.inclusion[0]
        assert entity.negation is True
        assert "heart" in entity.attribute.lower() or "failure" in entity.attribute.lower()


class TestTemporalConstraints:
    """Task 2.5-2.6: Test temporal constraint extraction."""

    def test_within_hours(self, extractor):
        """Should extract 'within 24 hours' temporal constraint."""
        criteria = "Inclusion: Septic shock within 24 hours of ICU admission"

        result = extractor.extract(criteria)

        assert len(result.inclusion) >= 1
        entity = result.inclusion[0]
        assert entity.temporal_constraint is not None
        assert entity.temporal_constraint.operator == "within_last"
        assert entity.temporal_constraint.value == 24
        assert entity.temporal_constraint.unit == "hours"

    def test_within_months(self, extractor):
        """Should extract 'within 6 months' temporal constraint."""
        criteria = "Exclusion: Myocardial infarction within 6 months"

        result = extractor.extract(criteria)

        assert len(result.exclusion) >= 1
        entity = result.exclusion[0]
        assert entity.temporal_constraint is not None
        assert entity.temporal_constraint.value == 6
        assert entity.temporal_constraint.unit == "months"

    def test_before_reference_point(self, extractor):
        """Should extract 'before admission' temporal constraint."""
        criteria = "Inclusion: Antibiotic therapy before admission"

        result = extractor.extract(criteria)

        assert len(result.inclusion) >= 1
        entity = result.inclusion[0]
        # May or may not extract temporal (acceptable both ways)
        if entity.temporal_constraint:
            assert entity.temporal_constraint.operator in ["before", "within_last"]


class TestComplexCriteria:
    """Task 2.7-2.8: Test complex criteria with sub_criteria."""

    def test_and_logic_subcriteria(self, extractor):
        """Should parse AND logic into sub_criteria."""
        criteria = """
        Inclusion: Septic shock defined as MAP e65 mmHg AND Lactate >2 mmol/L
        """

        result = extractor.extract(criteria)

        assert len(result.inclusion) >= 1
        # Find the entity with sub_criteria
        parent = None
        for entity in result.inclusion:
            if entity.sub_criteria and len(entity.sub_criteria) >= 2:
                parent = entity
                break

        assert parent is not None, "Should have entity with sub_criteria"
        assert len(parent.sub_criteria) >= 2

        # Check that MAP and Lactate are in sub_criteria
        attributes = [sc.attribute.lower() for sc in parent.sub_criteria]
        assert any("map" in attr or "pressure" in attr for attr in attributes)
        assert any("lactate" in attr for attr in attributes)

    def test_or_logic_subcriteria(self, extractor):
        """Should handle OR logic (may create multiple entities or sub_criteria)."""
        criteria = "Inclusion: Age > 65 OR chronic kidney disease"

        result = extractor.extract(criteria)

        # Accept either: 2 separate entities OR 1 entity with sub_criteria
        total_entities = len(result.inclusion)
        has_subcriteria = any(e.sub_criteria for e in result.inclusion)

        assert total_entities >= 1
        # Either multiple entities OR sub_criteria present
        assert total_entities >= 2 or has_subcriteria


class TestEdgeCases:
    """Task 2.9: Test edge cases and error handling."""

    def test_empty_criteria(self, extractor):
        """Should return empty arrays for empty input."""
        criteria = ""

        result = extractor.extract(criteria)

        assert isinstance(result, ExtractionOutput)
        assert result.inclusion == []
        assert result.exclusion == []

    def test_irrelevant_text(self, extractor):
        """Should return empty arrays for non-criteria text."""
        criteria = "Participants will be contacted by phone for follow-up."

        result = extractor.extract(criteria)

        # Should return empty or very few entities
        assert len(result.inclusion) + len(result.exclusion) <= 1

    def test_assumptions_tracking(self, extractor):
        """Should track assumptions when inferring values."""
        criteria = "Inclusion: Adult patients"

        result = extractor.extract(criteria)

        assert len(result.inclusion) >= 1
        entity = result.inclusion[0]
        # Should have assumed age >= 18
        assert entity.attribute == "age"
        assert entity.operator in [">=", ">"]
        assert int(entity.value) == 18
        assert len(entity.assumptions_made) > 0
        assert "adult" in entity.assumptions_made[0].lower()


class TestRealWorldCase:
    """Task 2.1: Test with real NCT03389555 criteria."""

    def test_nct03389555_extraction(self, extractor, nct03389555_criteria):
        """Should successfully extract NCT03389555 criteria."""
        result = extractor.extract(nct03389555_criteria)

        # Basic assertions
        assert isinstance(result, ExtractionOutput)
        assert len(result.inclusion) >= 3  # Age, septic shock, ICU admission
        assert len(result.exclusion) >= 3  # Age < 18, pregnancy, etc.

        # Check specific criteria
        inclusion_attrs = [e.attribute.lower() for e in result.inclusion]
        exclusion_attrs = [e.attribute.lower() for e in result.exclusion]

        # Inclusion should have age, septic shock components
        assert any("age" in attr for attr in inclusion_attrs)

        # Exclusion should have pregnancy
        assert any("pregnan" in attr for attr in exclusion_attrs)

        # Should have some temporal constraints (within 24 hours)
        has_temporal = any(
            e.temporal_constraint is not None
            for e in result.inclusion + result.exclusion
        )
        assert has_temporal, "Should extract temporal constraint 'within 24 hours'"

    def test_extraction_preserves_original_text(self, extractor, nct03389555_criteria):
        """Should preserve original criterion text in 'text' field."""
        result = extractor.extract(nct03389555_criteria)

        for entity in result.inclusion + result.exclusion:
            assert entity.text is not None
            assert len(entity.text) > 0
            # Text should be meaningful (not just whitespace)
            assert entity.text.strip() == entity.text
