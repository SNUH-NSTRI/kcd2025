"""
Unit tests for EligibilityExtractor.

Following TDD principles:
1. Write test first
2. Implement to make test pass
3. Refactor while keeping tests green
"""

import json
import os
from pathlib import Path

import pytest

from backend.src.pipeline.plugins.eligibility_extractor import EligibilityExtractor
from backend.src.rwe_api.schemas.eligibility_schemas import (
    EligibilityExtraction,
    EligibilityCriterion,
)


def load_seed_example(filename: str) -> dict:
    """Load a seed example from workspace/corrections/seed_examples/."""
    seed_dir = Path(__file__).parents[4] / "workspace" / "corrections" / "seed_examples"
    seed_path = seed_dir / filename

    if not seed_path.exists():
        pytest.skip(f"Seed example not found: {seed_path}")

    with open(seed_path, "r") as f:
        return json.load(f)


def create_mock_nct_data(nct_id: str, eligibility_text: str) -> dict:
    """Create mock NCT data for testing."""
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id},
            "eligibilityModule": {"eligibilityCriteria": eligibility_text},
        }
    }


class TestExtractEligibilitySection:
    """Test the _extract_eligibility_section method."""

    def test_extracts_inclusion_and_exclusion_from_nct_data(self):
        """Should extract and concatenate inclusion and exclusion criteria from NCT JSON."""
        # Arrange
        mock_nct_data = {
            "protocolSection": {
                "eligibilityModule": {
                    "eligibilityCriteria": """
                    Inclusion Criteria:
                    - Age 18 years or older
                    - Confirmed diagnosis of septic shock

                    Exclusion Criteria:
                    - Pregnancy or breastfeeding
                    - Terminal illness
                    """
                }
            }
        }

        extractor = EligibilityExtractor()

        # Act
        eligibility_text = extractor._extract_eligibility_section(mock_nct_data)

        # Assert
        assert "Age 18 years or older" in eligibility_text
        assert "Confirmed diagnosis of septic shock" in eligibility_text
        assert "Pregnancy or breastfeeding" in eligibility_text
        assert "Terminal illness" in eligibility_text

    def test_handles_missing_eligibility_module(self):
        """Should return empty string if eligibility module is missing."""
        # Arrange
        mock_nct_data = {"protocolSection": {}}
        extractor = EligibilityExtractor()

        # Act
        eligibility_text = extractor._extract_eligibility_section(mock_nct_data)

        # Assert
        assert eligibility_text == ""

    def test_handles_empty_eligibility_criteria(self):
        """Should return empty string if eligibility criteria is empty."""
        # Arrange
        mock_nct_data = {
            "protocolSection": {
                "eligibilityModule": {
                    "eligibilityCriteria": ""
                }
            }
        }
        extractor = EligibilityExtractor()

        # Act
        eligibility_text = extractor._extract_eligibility_section(mock_nct_data)

        # Assert
        assert eligibility_text == ""


class TestBuildPrompt:
    """Test the _build_prompt method."""

    def test_builds_few_shot_prompt_with_examples(self):
        """Should build a prompt with system message, examples, and query text."""
        # Arrange
        eligibility_text = "Age >= 18 years. ECOG performance status 0-1."
        examples = [
            {
                "nct_id": "NCT03389555",
                "extraction": {
                    "human_corrected": {
                        "inclusion": [
                            {
                                "id": "inc_1",
                                "type": "inclusion",
                                "key": "Age",
                                "operator": ">=",
                                "value": 18,
                                "unit": "years",
                                "original_text": "Age 18 years or older"
                            }
                        ],
                        "exclusion": []
                    }
                }
            }
        ]

        extractor = EligibilityExtractor()

        # Act
        prompt = extractor._build_prompt(eligibility_text, examples)

        # Assert
        assert "system" in prompt.lower() or "extract" in prompt.lower()
        assert "NCT03389555" in prompt
        assert "Age >= 18 years" in prompt
        assert "ECOG performance status 0-1" in prompt

    def test_builds_prompt_without_examples_for_cold_start(self):
        """Should build a valid prompt even with zero examples (cold start)."""
        # Arrange
        eligibility_text = "Age >= 18 years."
        examples = []

        extractor = EligibilityExtractor()

        # Act
        prompt = extractor._build_prompt(eligibility_text, examples)

        # Assert
        assert "Age >= 18 years" in prompt
        assert len(prompt) > 0


# Integration tests (require API key)
class TestExtractMethodIntegration:
    """Integration tests for the extract method (requires LLM API)."""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY is not set"
    )
    def test_extract_with_real_llm_and_seed_examples(self):
        """
        Integration test: Extract with real LLM using seed examples.

        This test validates:
        1. LLM call completes without errors
        2. Response is parsed into valid EligibilityExtraction
        3. Basic structure and types are correct
        """
        # Arrange: Load seed examples
        seed_examples = [
            load_seed_example("NCT03389555_sepsis.json"),
            load_seed_example("NCT00000002_diabetes.json"),
        ]

        # Create mock NCT data with realistic eligibility text
        eligibility_text = """
        Inclusion Criteria:
        - Age 18 years or older
        - Confirmed diagnosis of septic shock requiring vasopressor therapy
        - Written informed consent obtained from patient or legal representative

        Exclusion Criteria:
        - Age less than 18 years
        - Pregnant or breastfeeding women
        - Terminal illness with life expectancy less than 24 hours
        """

        nct_data = create_mock_nct_data("NCT99999999", eligibility_text)

        # Initialize extractor
        extractor = EligibilityExtractor(model_name="gpt-4o-mini", temperature=0.0)

        # Act: Run the extraction (MAKES REAL API CALL)
        result = extractor.extract(nct_data, examples=seed_examples)

        # Assert: Validate structure and types
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "inclusion" in result, "Result should contain 'inclusion'"
        assert "exclusion" in result, "Result should contain 'exclusion'"
        assert "confidence_score" in result, "Result should contain 'confidence_score'"

        # Validate confidence score
        assert isinstance(
            result["confidence_score"], float
        ), "Confidence score should be float"
        assert (
            0.0 <= result["confidence_score"] <= 1.0
        ), "Confidence score should be between 0.0 and 1.0"

        # Validate lists
        assert isinstance(result["inclusion"], list), "Inclusion should be a list"
        assert isinstance(result["exclusion"], list), "Exclusion should be a list"

        # Validate that at least some criteria were extracted
        assert (
            len(result["inclusion"]) > 0 or len(result["exclusion"]) > 0
        ), "Should extract at least one criterion"

        # If criteria exist, validate their structure
        all_criteria = result["inclusion"] + result["exclusion"]
        if all_criteria:
            first_criterion = all_criteria[0]
            required_fields = [
                "id",
                "type",
                "key",
                "operator",
                "value",
                "original_text",
            ]
            for field in required_fields:
                assert (
                    field in first_criterion
                ), f"Criterion should have '{field}' field"

        # Print results for manual inspection
        print("\n=== Extraction Result ===")
        print(f"Confidence Score: {result['confidence_score']}")
        print(f"Inclusion Count: {len(result['inclusion'])}")
        print(f"Exclusion Count: {len(result['exclusion'])}")

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY is not set"
    )
    def test_extract_with_zero_examples_cold_start(self):
        """
        Integration test: Extract without any examples (cold start).

        Tests that the system can still function with zero examples.
        """
        # Arrange: No examples
        seed_examples = []

        eligibility_text = """
        Inclusion Criteria:
        - Age between 18 and 75 years
        - Type 2 diabetes for at least 6 months

        Exclusion Criteria:
        - Pregnancy
        """

        nct_data = create_mock_nct_data("NCT88888888", eligibility_text)

        # Initialize extractor
        extractor = EligibilityExtractor(model_name="gpt-4o-mini", temperature=0.0)

        # Act: Run extraction with zero examples
        result = extractor.extract(nct_data, examples=seed_examples)

        # Assert: Should still produce valid output
        assert isinstance(result, dict)
        assert "inclusion" in result
        assert "exclusion" in result
        assert (
            len(result["inclusion"]) > 0 or len(result["exclusion"]) > 0
        ), "Should extract criteria even without examples"
