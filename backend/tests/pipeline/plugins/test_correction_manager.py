"""
Unit tests for CorrectionManager.

Following TDD principles:
1. Write test first (Red)
2. Implement to make test pass (Green)
3. Refactor while keeping tests green (Refactor)
"""

import json
import multiprocessing
from pathlib import Path

import pytest

from backend.src.pipeline.plugins.correction_manager import CorrectionManager


class TestQualityScoring:
    """Test the quality scoring logic (pure function)."""

    def test_default_score_for_normal_user_correction(self):
        """Normal user corrections should start with score 0.75."""
        correction_data = {
            "nct_id": "NCT12345678",
            "corrected_by": "user@example.com",
            "extraction": {
                "original_ai_output": {
                    "inclusion": [{"id": "inc_1"}],
                    "exclusion": [],
                },
                "human_corrected": {
                    "inclusion": [
                        {
                            "id": "inc_1",
                            "value": "CHANGED",
                            "original_text": "Age 18 years or older",  # Long enough text
                        }
                    ],
                    "exclusion": [],
                },
                "changes": [{"field": "inclusion[0].value"}],  # Only 1 change
            },
        }

        score = CorrectionManager._calculate_quality_score(correction_data)

        assert score == 0.75, "Normal user correction should have base score of 0.75"

    def test_perfect_score_for_seed_examples(self):
        """Seed examples should have quality score 1.0."""
        seed_data = {
            "nct_id": "NCT03389555",
            "corrected_by": "seed_curator",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {"inclusion": [{"id": "inc_1"}], "exclusion": []},
                "changes": [],
            },
        }

        score = CorrectionManager._calculate_quality_score(seed_data)

        assert score == 1.0, "Seed examples should have perfect score"

    def test_penalty_for_too_many_changes(self):
        """Should reduce score if user made > 10 changes."""
        correction_with_many_changes = {
            "nct_id": "NCT12345678",
            "corrected_by": "user@example.com",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {"inclusion": [], "exclusion": []},
                "changes": [{"field": f"field_{i}"} for i in range(15)],  # 15 changes
            },
        }

        score = CorrectionManager._calculate_quality_score(correction_with_many_changes)

        assert score < 0.75, "Should penalize for > 10 changes"
        assert score >= 0.0, "Score should not go below 0.0"

    def test_penalty_for_empty_inclusion(self):
        """Should reduce score if inclusion criteria is empty."""
        correction_empty_inclusion = {
            "nct_id": "NCT12345678",
            "corrected_by": "user@example.com",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {
                    "inclusion": [],  # Empty inclusion
                    "exclusion": [{"id": "exc_1"}],
                },
                "changes": [],
            },
        }

        score = CorrectionManager._calculate_quality_score(correction_empty_inclusion)

        assert score < 0.75, "Should penalize for empty inclusion"

    def test_penalty_for_very_short_text(self):
        """Should reduce score if original_text is very short (< 5 chars)."""
        correction_short_text = {
            "nct_id": "NCT12345678",
            "corrected_by": "user@example.com",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {
                    "inclusion": [
                        {
                            "id": "inc_1",
                            "original_text": "Age",  # Too short
                        }
                    ],
                    "exclusion": [],
                },
                "changes": [],
            },
        }

        score = CorrectionManager._calculate_quality_score(correction_short_text)

        assert score < 0.75, "Should penalize for very short text"

    def test_score_clamped_between_zero_and_one(self):
        """Quality score should always be between 0.0 and 1.0."""
        # Create worst-case scenario
        worst_correction = {
            "nct_id": "NCT12345678",
            "corrected_by": "user@example.com",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {"inclusion": [], "exclusion": []},  # Empty both
                "changes": [{"field": f"field_{i}"} for i in range(20)],  # Many changes
            },
        }

        score = CorrectionManager._calculate_quality_score(worst_correction)

        assert 0.0 <= score <= 1.0, "Score should be clamped between 0.0 and 1.0"


class TestInitializationAndColdStart:
    """Test initialization and cold start behavior."""

    def test_creates_index_on_first_init(self, tmp_path):
        """Should create index.json if it doesn't exist."""
        # Arrange: Empty directory
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()

        # Act: Initialize manager
        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        # Assert: index.json should be created
        index_path = corrections_dir / "index.json"
        assert index_path.exists(), "index.json should be created"

        # Assert: Should have correct structure
        with open(index_path, "r") as f:
            index = json.load(f)

        assert "trials" in index
        assert "by_condition" in index
        assert "by_keyword" in index
        assert "recent" in index
        assert isinstance(index["trials"], dict)
        assert isinstance(index["recent"], list)

    def test_loads_existing_index_without_overwriting(self, tmp_path):
        """Should load existing index without overwriting it."""
        # Arrange: Create index with some data
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()
        index_path = corrections_dir / "index.json"

        existing_data = {
            "trials": {"NCT12345678": {"latest_version": "v1"}},
            "by_condition": {},
            "by_keyword": {},
            "recent": ["NCT12345678"],
        }

        with open(index_path, "w") as f:
            json.dump(existing_data, f)

        # Act: Initialize manager
        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        # Assert: Existing data should be preserved
        with open(index_path, "r") as f:
            index = json.load(f)

        assert "NCT12345678" in index["trials"]
        assert index["trials"]["NCT12345678"]["latest_version"] == "v1"


class TestSaveCorrection:
    """Test save_correction() method with atomic write behavior."""

    def test_save_correction_creates_file_and_updates_index(self, tmp_path):
        """First correction for a trial should create file and update index."""
        # Arrange
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()
        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        correction_data = {
            "nct_id": "NCT12345678",
            "corrected_by": "test_user@example.com",
            "timestamp": "2025-01-15T10:00:00Z",
            "extraction": {
                "original_ai_output": {
                    "inclusion": [{"id": "inc_1", "value": "Age >= 18"}],
                    "exclusion": [],
                },
                "human_corrected": {
                    "inclusion": [
                        {
                            "id": "inc_1",
                            "value": "Age 18 years or older",
                            "original_text": "Adults aged 18 and above",
                        }
                    ],
                    "exclusion": [],
                },
                "changes": [{"field": "inclusion[0].value", "from": "Age >= 18", "to": "Age 18 years or older"}],
            },
        }

        # Act
        result = manager.save_correction(correction_data)

        # Assert: Returns success with version
        assert result["success"] is True
        assert "version" in result
        assert result["version"] == "v1"

        # Assert: File created
        trial_file = corrections_dir / "data" / "NCT12345678.json"
        assert trial_file.exists()

        # Assert: Index updated
        index_path = corrections_dir / "index.json"
        with open(index_path, "r") as f:
            index = json.load(f)

        assert "NCT12345678" in index["trials"]
        assert index["trials"]["NCT12345678"]["latest_version"] == "v1"
        assert index["trials"]["NCT12345678"]["correction_count"] == 1

    def test_save_correction_appends_to_existing_file(self, tmp_path):
        """Second correction should append as v2 without losing v1."""
        # Arrange
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()
        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        first_correction = {
            "nct_id": "NCT12345678",
            "corrected_by": "user1@example.com",
            "timestamp": "2025-01-15T10:00:00Z",
            "extraction": {
                "original_ai_output": {"inclusion": [{"id": "inc_1"}], "exclusion": []},
                "human_corrected": {"inclusion": [{"id": "inc_1", "value": "First version"}], "exclusion": []},
                "changes": [{"field": "inclusion[0].value"}],
            },
        }

        second_correction = {
            "nct_id": "NCT12345678",
            "corrected_by": "user2@example.com",
            "timestamp": "2025-01-15T11:00:00Z",
            "extraction": {
                "original_ai_output": {"inclusion": [{"id": "inc_1"}], "exclusion": []},
                "human_corrected": {"inclusion": [{"id": "inc_1", "value": "Second version"}], "exclusion": []},
                "changes": [{"field": "inclusion[0].value"}],
            },
        }

        # Act
        manager.save_correction(first_correction)
        result = manager.save_correction(second_correction)

        # Assert: Second correction is v2
        assert result["version"] == "v2"

        # Assert: Both versions exist in file
        trial_file = corrections_dir / "data" / "NCT12345678.json"
        with open(trial_file, "r") as f:
            data = json.load(f)

        assert "versions" in data
        assert len(data["versions"]) == 2
        assert data["versions"]["v1"]["corrected_by"] == "user1@example.com"
        assert data["versions"]["v2"]["corrected_by"] == "user2@example.com"

    def test_save_correction_calculates_quality_score(self, tmp_path):
        """Should calculate and store quality score for each correction."""
        # Arrange
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()
        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        correction_data = {
            "nct_id": "NCT12345678",
            "corrected_by": "test_user@example.com",
            "timestamp": "2025-01-15T10:00:00Z",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {
                    "inclusion": [
                        {"id": "inc_1", "original_text": "Age 18 years or older"}  # Long enough text
                    ],
                    "exclusion": [],
                },
                "changes": [{"field": "inclusion[0]"}],
            },
        }

        # Act
        manager.save_correction(correction_data)

        # Assert: Quality score stored
        trial_file = corrections_dir / "data" / "NCT12345678.json"
        with open(trial_file, "r") as f:
            data = json.load(f)

        assert "quality_score" in data["versions"]["v1"]
        assert 0.0 <= data["versions"]["v1"]["quality_score"] <= 1.0


class TestSelectExamples:
    """Test select_examples() method with hybrid selection strategy."""

    def test_select_examples_cold_start_returns_seed_examples(self, tmp_path):
        """When no corrections exist, should return seed examples."""
        # Arrange
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()
        (corrections_dir / "data").mkdir()
        seed_dir = corrections_dir / "seed_examples"
        seed_dir.mkdir()

        # Create 3 seed examples
        for i in range(1, 4):
            seed_file = seed_dir / f"NCT0000000{i}.json"
            with open(seed_file, "w") as f:
                json.dump(
                    {
                        "nct_id": f"NCT0000000{i}",
                        "corrected_by": "seed_curator",
                        "extraction": {"inclusion": [], "exclusion": []},
                    },
                    f,
                )

        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        study_metadata = {
            "condition": "sepsis",
            "keywords": ["age_criteria"],
        }

        # Act
        examples = manager.select_examples(study_metadata, num=3)

        # Assert
        assert len(examples) == 3
        assert all(ex["corrected_by"] == "seed_curator" for ex in examples)

    def test_select_examples_prefers_condition_match(self, tmp_path):
        """Should prioritize examples with matching condition."""
        # Arrange
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()
        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        # Save corrections for different conditions
        sepsis_correction = {
            "nct_id": "NCT11111111",
            "corrected_by": "user1@example.com",
            "timestamp": "2025-01-15T10:00:00Z",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {
                    "inclusion": [{"id": "inc_1", "original_text": "Sepsis diagnosis"}],
                    "exclusion": [],
                },
                "changes": [],
            },
            "metadata": {"condition": "sepsis", "keywords": []},
        }

        diabetes_correction = {
            "nct_id": "NCT22222222",
            "corrected_by": "user2@example.com",
            "timestamp": "2025-01-15T11:00:00Z",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {
                    "inclusion": [{"id": "inc_1", "original_text": "Type 2 diabetes"}],
                    "exclusion": [],
                },
                "changes": [],
            },
            "metadata": {"condition": "diabetes", "keywords": []},
        }

        manager.save_correction(sepsis_correction)
        manager.save_correction(diabetes_correction)

        study_metadata = {"condition": "sepsis", "keywords": []}

        # Act
        examples = manager.select_examples(study_metadata, num=2)

        # Assert: Sepsis example should be first
        assert len(examples) >= 1
        # First example should be the sepsis one
        assert examples[0]["nct_id"] == "NCT11111111"

    def test_select_examples_uses_keyword_overlap_as_secondary(self, tmp_path):
        """Should use keyword overlap when condition doesn't match."""
        # Arrange
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()
        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        correction_with_keyword = {
            "nct_id": "NCT33333333",
            "corrected_by": "user@example.com",
            "timestamp": "2025-01-15T10:00:00Z",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {
                    "inclusion": [{"id": "inc_1", "original_text": "Age >= 18 years"}],
                    "exclusion": [],
                },
                "changes": [],
            },
            "metadata": {"condition": "cancer", "keywords": ["age_criteria"]},
        }

        manager.save_correction(correction_with_keyword)

        study_metadata = {"condition": "sepsis", "keywords": ["age_criteria"]}

        # Act
        examples = manager.select_examples(study_metadata, num=1)

        # Assert: Should return the example with keyword overlap
        assert len(examples) == 1
        assert examples[0]["nct_id"] == "NCT33333333"

    def test_select_examples_filters_by_quality_score(self, tmp_path):
        """Should only return corrections with quality_score >= 0.7."""
        # Arrange
        corrections_dir = tmp_path / "corrections"
        corrections_dir.mkdir()
        manager = CorrectionManager(corrections_dir=str(corrections_dir))

        # Low quality correction (empty inclusion → score < 0.7)
        low_quality = {
            "nct_id": "NCT44444444",
            "corrected_by": "user@example.com",
            "timestamp": "2025-01-15T10:00:00Z",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {
                    "inclusion": [],  # Empty → penalty
                    "exclusion": [],
                },
                "changes": [],
            },
            "metadata": {"condition": "sepsis", "keywords": []},
        }

        # High quality correction
        high_quality = {
            "nct_id": "NCT55555555",
            "corrected_by": "user@example.com",
            "timestamp": "2025-01-15T11:00:00Z",
            "extraction": {
                "original_ai_output": {"inclusion": [], "exclusion": []},
                "human_corrected": {
                    "inclusion": [{"id": "inc_1", "original_text": "Valid criteria here"}],
                    "exclusion": [],
                },
                "changes": [],
            },
            "metadata": {"condition": "sepsis", "keywords": []},
        }

        manager.save_correction(low_quality)
        manager.save_correction(high_quality)

        study_metadata = {"condition": "sepsis", "keywords": []}

        # Act
        examples = manager.select_examples(study_metadata, num=5)

        # Assert: Should only include high quality example
        nct_ids = [ex["nct_id"] for ex in examples]
        assert "NCT55555555" in nct_ids
        assert "NCT44444444" not in nct_ids


# TODO: Implement remaining test classes
# class TestAtomicWrites:
