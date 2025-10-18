"""Unit tests for Statistician Agent utilities.

Following TDD principles from vooster-docs/tdd.md:
- Test behavior, not implementation
- AAA pattern (Arrange, Act, Assert)
- Fast, Independent, Repeatable tests
"""

import pytest
from pathlib import Path
from agents.statistician.utils import (
    sanitize_medication_name,
    construct_cohort_path,
    construct_output_dir,
    validate_nct_id,
    validate_medication,
)


class TestSanitizeMedicationName:
    """Test medication name sanitization."""

    def test_removes_spaces_and_dots(self):
        # Arrange & Act
        result = sanitize_medication_name("hydrocortisone na succ.")

        # Assert
        assert result == "hydrocortisonenasucc"

    def test_converts_to_lowercase(self):
        # Arrange & Act
        result = sanitize_medication_name("Dexamethasone")

        # Assert
        assert result == "dexamethasone"

    def test_removes_hyphens(self):
        # Arrange & Act
        result = sanitize_medication_name("methyl-prednisolone")

        # Assert
        assert result == "methylprednisolone"

    def test_removes_special_characters(self):
        # Arrange & Act
        result = sanitize_medication_name("drug@#$%123")

        # Assert
        assert result == "drug123"

    def test_empty_string_returns_empty(self):
        # Arrange & Act
        result = sanitize_medication_name("")

        # Assert
        assert result == ""


class TestValidateNctId:
    """Test NCT ID validation."""

    def test_valid_nct_id(self):
        # Arrange & Act
        is_valid, error = validate_nct_id("NCT03389555")

        # Assert
        assert is_valid is True
        assert error is None

    def test_empty_nct_id(self):
        # Arrange & Act
        is_valid, error = validate_nct_id("")

        # Assert
        assert is_valid is False
        assert "cannot be empty" in error

    def test_missing_nct_prefix(self):
        # Arrange & Act
        is_valid, error = validate_nct_id("03389555")

        # Assert
        assert is_valid is False
        assert "must start with 'NCT'" in error

    def test_invalid_digit_count(self):
        # Arrange & Act
        is_valid, error = validate_nct_id("NCT123")

        # Assert
        assert is_valid is False
        assert "8 digits" in error

    def test_non_numeric_digits(self):
        # Arrange & Act
        is_valid, error = validate_nct_id("NCT0338955A")

        # Assert
        assert is_valid is False
        assert "8 digits" in error


class TestValidateMedication:
    """Test medication validation."""

    def test_valid_medication(self):
        # Arrange & Act
        is_valid, error = validate_medication("hydrocortisone")

        # Assert
        assert is_valid is True
        assert error is None

    def test_empty_medication(self):
        # Arrange & Act
        is_valid, error = validate_medication("")

        # Assert
        assert is_valid is False
        assert "cannot be empty" in error

    def test_whitespace_only(self):
        # Arrange & Act
        is_valid, error = validate_medication("   ")

        # Assert
        assert is_valid is False
        assert "cannot be empty" in error

    def test_medication_with_spaces(self):
        # Arrange & Act
        is_valid, error = validate_medication("hydrocortisone na succ.")

        # Assert
        assert is_valid is True
        assert error is None

    def test_very_short_after_sanitization(self):
        # Arrange & Act
        is_valid, error = validate_medication("..")

        # Assert
        assert is_valid is False
        assert ("too short" in error or "empty string" in error)


class TestConstructCohortPath:
    """Test cohort path construction."""

    def test_construct_valid_path(self, tmp_path):
        # Arrange
        nct_id = "NCT03389555"
        medication = "hydrocortisone na succ."

        # Create expected file structure
        cohort_dir = tmp_path / nct_id / "cohorts" / "hydrocortisonenasucc"
        cohort_dir.mkdir(parents=True)
        cohort_file = cohort_dir / f"{nct_id}_hydrocortisonenasucc_v3.1_with_baseline.csv"
        cohort_file.write_text("dummy,data\n1,2")

        # Act
        result = construct_cohort_path(nct_id, medication, workspace_root=tmp_path)

        # Assert
        assert result == cohort_file
        assert result.exists()

    def test_file_not_found_raises_error(self, tmp_path):
        # Arrange
        nct_id = "NCT03389555"
        medication = "nonexistent"

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            construct_cohort_path(nct_id, medication, workspace_root=tmp_path)

        assert "not found" in str(exc_info.value)

    def test_invalid_nct_id_raises_error(self, tmp_path):
        # Arrange
        nct_id = "INVALID"
        medication = "test"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            construct_cohort_path(nct_id, medication, workspace_root=tmp_path)

        assert "Invalid NCT ID" in str(exc_info.value)


class TestConstructOutputDir:
    """Test output directory construction."""

    def test_creates_output_dir(self, tmp_path):
        # Arrange
        nct_id = "NCT03389555"
        medication = "hydrocortisone"

        # Act
        result = construct_output_dir(nct_id, medication, workspace_root=tmp_path)

        # Assert
        assert result.exists()
        assert result.is_dir()
        assert result.name == "outputs"

    def test_output_dir_path_format(self, tmp_path):
        # Arrange
        nct_id = "NCT03389555"
        medication = "hydrocortisone na succ."

        # Act
        result = construct_output_dir(nct_id, medication, workspace_root=tmp_path)

        # Assert
        expected = tmp_path / nct_id / "cohorts" / "hydrocortisonenasucc" / "outputs"
        assert result == expected

    def test_idempotent_creation(self, tmp_path):
        # Arrange
        nct_id = "NCT03389555"
        medication = "test"

        # Act - call twice
        result1 = construct_output_dir(nct_id, medication, workspace_root=tmp_path)
        result2 = construct_output_dir(nct_id, medication, workspace_root=tmp_path)

        # Assert - should succeed both times
        assert result1 == result2
        assert result1.exists()
