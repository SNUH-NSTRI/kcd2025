"""
Integration tests for TrialistHybridPipeline.

Tests end-to-end execution of all 3 stages with error aggregation
and summary statistics.
"""

import os
import pytest

from backend.src.agents.trialist_hybrid.pipeline import TrialistHybridPipeline
from backend.src.agents.trialist_hybrid.models import PipelineOutput


@pytest.fixture
def api_key():
    """Get OpenRouter API key from environment."""
    return os.getenv("OPENROUTER_API_KEY", "test_key")


@pytest.fixture
def schema_path():
    """Path to MIMIC-IV schema."""
    return os.path.join(
        os.path.dirname(__file__),
        "../../..",
        "src/agents/trialist_hybrid/prompts/mimic_schema.json"
    )


@pytest.fixture
def nct03389555_criteria():
    """Load NCT03389555 criteria fixture."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "fixtures/nct03389555_criteria.txt"
    )
    with open(fixture_path, "r") as f:
        return f.read()


class TestPipelineExecution:
    """Test full pipeline execution."""

    def test_simple_criteria_full_pipeline(self, api_key, schema_path):
        """Should execute all 3 stages for simple age criterion."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        raw_criteria = "Inclusion: Adult patients aged 18 years or older"
        result = pipeline.run(raw_criteria)

        # Check result structure
        assert isinstance(result, PipelineOutput)
        assert result.extraction is not None
        assert len(result.extraction.inclusion) > 0

        # Check mapping results
        assert result.mappings is not None
        assert len(result.mappings) > 0

        # Check validation results
        assert result.validations is not None
        assert len(result.validations) > 0

        # Check summary
        assert result.summary is not None
        assert result.summary.total_criteria > 0
        assert result.summary.stage1_extracted >= 0
        assert result.summary.stage2_mapped >= 0
        assert result.summary.stage3_passed >= 0

    def test_empty_criteria_graceful(self, api_key, schema_path):
        """Should handle empty criteria gracefully."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        result = pipeline.run("")

        assert isinstance(result, PipelineOutput)
        assert result.extraction is not None
        assert len(result.extraction.inclusion) == 0
        assert len(result.extraction.exclusion) == 0
        assert result.summary.total_criteria == 0

    def test_mixed_inclusion_exclusion(self, api_key, schema_path):
        """Should handle both inclusion and exclusion criteria."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        raw_criteria = """
        Inclusion:
        - Age >= 18 years
        - Sepsis diagnosis

        Exclusion:
        - Pregnancy
        - Prior myocardial infarction
        """

        result = pipeline.run(raw_criteria)

        assert isinstance(result, PipelineOutput)
        assert len(result.extraction.inclusion) >= 2
        assert len(result.extraction.exclusion) >= 2
        assert result.summary.total_criteria >= 4


class TestErrorAggregation:
    """Test strict entity-level, lenient trial-level error handling."""

    def test_partial_success_lenient(self, api_key, schema_path):
        """Should allow partial success (3/5 criteria pass)."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        # Mix of valid and potentially invalid criteria
        raw_criteria = """
        Inclusion:
        - Age >= 18 years
        - Lactate > 2 mmol/L
        - Some ambiguous medical condition XYZ123
        """

        result = pipeline.run(raw_criteria)

        # Pipeline should complete even with some failures
        assert isinstance(result, PipelineOutput)
        assert result.summary.total_criteria >= 3

        # At least some criteria should pass
        assert result.summary.stage3_passed + result.summary.stage3_warning >= 1

    def test_all_criteria_fail_gracefully(self, api_key, schema_path):
        """Should handle all criteria failing gracefully."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        # Completely irrelevant text
        raw_criteria = "This is not a clinical trial criterion at all."

        result = pipeline.run(raw_criteria)

        assert isinstance(result, PipelineOutput)
        # Should have zero or very low extraction
        assert result.summary.stage1_extracted == 0 or result.summary.stage3_passed == 0


class TestSummaryStatistics:
    """Test summary statistics generation."""

    def test_summary_counts_accurate(self, api_key, schema_path):
        """Should generate accurate summary counts."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        raw_criteria = """
        Inclusion:
        - Age >= 18 years
        - Lactate > 2 mmol/L
        """

        result = pipeline.run(raw_criteria)

        summary = result.summary

        # Total should match extractions
        assert summary.total_criteria == len(result.extraction.inclusion) + len(result.extraction.exclusion)

        # Stage counts should be consistent
        assert summary.stage1_extracted <= summary.total_criteria
        assert summary.stage2_mapped <= summary.stage1_extracted
        assert summary.stage3_passed + summary.stage3_warning + summary.stage3_needs_review + summary.stage3_failed <= summary.stage2_mapped

    def test_summary_percentages(self, api_key, schema_path):
        """Should include success rates in summary."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        raw_criteria = "Inclusion: Age >= 18 years"
        result = pipeline.run(raw_criteria)

        summary = result.summary

        # Should have percentage fields
        assert hasattr(summary, 'stage1_extraction_rate')
        assert hasattr(summary, 'stage2_mapping_rate')
        assert hasattr(summary, 'stage3_validation_rate')

        # Rates should be between 0 and 1
        if summary.total_criteria > 0:
            assert 0 <= summary.stage1_extraction_rate <= 1
            assert 0 <= summary.stage2_mapping_rate <= 1
            assert 0 <= summary.stage3_validation_rate <= 1


class TestRealWorldCase:
    """Test with real NCT03389555 criteria."""

    @pytest.mark.skip(reason="Requires valid OpenRouter API key")
    def test_nct03389555_full_pipeline(self, api_key, schema_path, nct03389555_criteria):
        """Should successfully parse NCT03389555 septic shock trial."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        result = pipeline.run(nct03389555_criteria)

        assert isinstance(result, PipelineOutput)

        # Should extract multiple criteria
        assert result.summary.total_criteria >= 5

        # Should have high success rate for well-defined trial
        assert result.summary.stage1_extraction_rate > 0.8
        assert result.summary.stage2_mapping_rate > 0.7

        # Should have at least some passed validations
        assert result.summary.stage3_passed > 0


class TestLoggingAndSaving:
    """Test logging and intermediate result saving."""

    def test_intermediate_results_available(self, api_key, schema_path):
        """Should provide access to intermediate stage results."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        raw_criteria = "Inclusion: Age >= 18 years"
        result = pipeline.run(raw_criteria)

        # All stage outputs should be accessible
        assert result.extraction is not None
        assert result.mappings is not None
        assert result.validations is not None

    def test_error_messages_informative(self, api_key, schema_path):
        """Should provide informative error messages."""
        pipeline = TrialistHybridPipeline(
            api_key=api_key,
            schema_path=schema_path
        )

        raw_criteria = "Completely invalid nonsense XYZ"
        result = pipeline.run(raw_criteria)

        # Should complete without raising exceptions
        assert isinstance(result, PipelineOutput)

        # Error information should be available
        if result.summary.stage3_failed > 0:
            # Check that validation results contain flag information
            assert any(len(v.flags) > 0 for v in result.validations)
