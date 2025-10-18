"""
Unit tests for the TrialistMimicMapper plugin.

Following TDD principles: Red → Green → Refactor
These are characterization tests for existing code to create a safety net.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Import from backend/src
from pipeline.plugins.trialist_mimic_mapper import TrialistMimicMapper
from tests.utils.sql_helpers import normalize_sql


@pytest.fixture
def mapper() -> TrialistMimicMapper:
    """Provides a fresh instance of TrialistMimicMapper for each test."""
    return TrialistMimicMapper()


class TestGenerateDemographicCTE:
    """Characterization tests for the _generate_demographic_cte method."""

    def test_should_generate_correct_sql_for_age_only(self, mapper: TrialistMimicMapper):
        """RED Phase: Test will fail until we verify current behavior."""
        # Arrange
        cte_name = "inc_1_demographic"
        
        # Mock the entity object with necessary attributes
        age_entity = MagicMock()
        age_entity.text = "age greater than 18"
        age_entity.operator = ">"
        age_entity.numeric_value = 18
        
        entities = [age_entity]
        
        expected_sql = f"""
        {cte_name} AS (
          SELECT DISTINCT subject_id
          FROM patients
          WHERE anchor_age > 18
        )
        """

        # Act
        generated_sql = mapper._generate_demographic_cte(cte_name, entities)

        # Assert
        assert normalize_sql(generated_sql) == normalize_sql(expected_sql)

    def test_should_generate_correct_sql_for_gender_female(self, mapper: TrialistMimicMapper):
        """Verify SQL generation for female gender condition."""
        # Arrange
        cte_name = "inc_2_demographic"
        
        gender_entity = MagicMock()
        gender_entity.text = "female patients"
        gender_entity.operator = None
        gender_entity.numeric_value = None
        
        entities = [gender_entity]
        
        expected_sql = f"""
        {cte_name} AS (
          SELECT DISTINCT subject_id
          FROM patients
          WHERE gender = 'F'
        )
        """

        # Act
        generated_sql = mapper._generate_demographic_cte(cte_name, entities)

        # Assert
        assert normalize_sql(generated_sql) == normalize_sql(expected_sql)

    def test_should_generate_correct_sql_for_gender_male(self, mapper: TrialistMimicMapper):
        """Verify SQL generation for male gender condition."""
        # Arrange
        cte_name = "inc_3_demographic"
        
        gender_entity = MagicMock()
        gender_entity.text = "male patients"
        gender_entity.operator = None
        gender_entity.numeric_value = None
        
        entities = [gender_entity]
        
        expected_sql = f"""
        {cte_name} AS (
          SELECT DISTINCT subject_id
          FROM patients
          WHERE gender = 'M'
        )
        """

        # Act
        generated_sql = mapper._generate_demographic_cte(cte_name, entities)

        # Assert
        assert normalize_sql(generated_sql) == normalize_sql(expected_sql)

    def test_should_combine_age_and_gender_with_and(self, mapper: TrialistMimicMapper):
        """Verify multiple demographic conditions are joined with AND."""
        # Arrange
        cte_name = "inc_4_demographic"
        
        age_entity = MagicMock()
        age_entity.text = "age <= 65"
        age_entity.operator = "<="
        age_entity.numeric_value = 65
        
        gender_entity = MagicMock()
        gender_entity.text = "male"
        gender_entity.operator = None
        gender_entity.numeric_value = None
        
        entities = [age_entity, gender_entity]
        
        expected_sql = f"""
        {cte_name} AS (
          SELECT DISTINCT subject_id
          FROM patients
          WHERE anchor_age <= 65 AND gender = 'M'
        )
        """

        # Act
        generated_sql = mapper._generate_demographic_cte(cte_name, entities)

        # Assert
        assert normalize_sql(generated_sql) == normalize_sql(expected_sql)

    def test_should_return_none_for_empty_entities_list(self, mapper: TrialistMimicMapper):
        """Verify it handles an empty list of entities gracefully."""
        # Arrange
        cte_name = "inc_5_demographic"
        entities = []

        # Act
        generated_sql = mapper._generate_demographic_cte(cte_name, entities)

        # Assert
        assert generated_sql is None


class TestGenerateIcdCTE:
    """
    Tests for ICD-based CTE generation, demonstrating dependency mocking.
    """

    def test_should_generate_correct_sql_with_mocked_concept_mapper(self, mapper: TrialistMimicMapper):
        """
        Verify SQL generation for _generate_icd_cte with a mocked dependency.
        """
        # Arrange
        cte_name = "inc_6_condition"
        table_name = "diagnoses_icd"

        # 1. Mock the dependency on the mapper instance
        mapper.concept_mapper = MagicMock()
        
        # 2. Define the return value for the mocked method call
        mapper.concept_mapper.map_entity.return_value = {
            "icd9_codes": ["410.01", "410.9"],
            "icd10_codes": ["I21.0%"]
        }
        
        # 3. Create a mock entity to pass to the method
        condition_entity = MagicMock()
        condition_entity.text = "myocardial infarction"
        entities = [condition_entity]

        expected_sql = f"""
        {cte_name} AS (
          SELECT DISTINCT subject_id
          FROM {table_name}
          WHERE (icd_code LIKE '410.01' OR icd_code LIKE '410.9' OR icd_code LIKE 'I21.0%')
        )
        """

        # Act
        generated_sql = mapper._generate_icd_cte(cte_name, entities, table_name)

        # Assert
        assert normalize_sql(generated_sql) == normalize_sql(expected_sql)
        
        # 4. (Optional but good practice) Assert the mock was called correctly
        mapper.concept_mapper.map_entity.assert_called_once_with(condition_entity)

    def test_should_return_none_when_no_icd_codes_found(self, mapper: TrialistMimicMapper):
        """Edge case: Entity has no ICD code mappings."""
        # Arrange
        cte_name = "exc_1_condition"
        table_name = "diagnoses_icd"

        mapper.concept_mapper = MagicMock()
        mapper.concept_mapper.map_entity.return_value = {
            "icd9_codes": [],
            "icd10_codes": []
        }
        
        entity = MagicMock()
        entity.text = "unknown condition"
        entities = [entity]

        # Act
        generated_sql = mapper._generate_icd_cte(cte_name, entities, table_name)

        # Assert
        assert generated_sql is None


class TestGenerateMeasurementTableCTE:
    """
    RED Phase: Tests for the new _generate_measurement_table_cte helper method.
    These tests will FAIL because the method doesn't exist yet.
    """

    def test_should_generate_correct_sql_for_labevents_with_multiple_conditions(
        self, mapper: TrialistMimicMapper
    ):
        """
        RED: This test drives the creation of the generic measurement CTE generator.
        It should fail with an AttributeError until the method is created.
        """
        # Arrange
        cte_name = "inc_1_measurement"
        table_name = "labevents"
        # Represents multiple lab value criteria: (itemids, operator, value)
        conditions = [
            ([50912], ">", 1.5),  # Creatinine
            ([50885], "<", 100.0),  # BNP
        ]

        expected_sql = f"""
        {cte_name} AS (
          SELECT DISTINCT subject_id
          FROM {table_name}
          WHERE (itemid IN (50912) AND valuenum > 1.5) OR (itemid IN (50885) AND valuenum < 100.0)
        )"""

        # Act
        # This will raise AttributeError because the method doesn't exist yet.
        generated_sql = mapper._generate_measurement_table_cte(
            cte_name, table_name, conditions
        )

        # Assert
        assert normalize_sql(generated_sql) == normalize_sql(expected_sql)

    def test_should_handle_single_condition_for_chartevents(self, mapper: TrialistMimicMapper):
        """
        RED: Test a simpler case with only one condition for a different table.
        """
        # Arrange
        cte_name = "exc_2_measurement"
        table_name = "chartevents"
        conditions = [([227008], "<", 40.0)]  # LVEF

        expected_sql = f"""
        {cte_name} AS (
          SELECT DISTINCT subject_id
          FROM {table_name}
          WHERE (itemid IN (227008) AND valuenum < 40.0)
        )"""

        # Act
        generated_sql = mapper._generate_measurement_table_cte(
            cte_name, table_name, conditions
        )

        # Assert
        assert normalize_sql(generated_sql) == normalize_sql(expected_sql)

    def test_should_return_none_for_empty_conditions_list(self, mapper: TrialistMimicMapper):
        """
        RED: Test the edge case where no conditions are provided.
        """
        # Arrange
        cte_name = "inc_3_measurement"
        table_name = "labevents"
        conditions = []

        # Act
        generated_sql = mapper._generate_measurement_table_cte(
            cte_name, table_name, conditions
        )

        # Assert
        assert generated_sql is None

    def test_should_handle_conditions_with_empty_itemids(self, mapper: TrialistMimicMapper):
        """
        REFACTOR phase: Edge case discovered - conditions with empty itemids should be skipped.
        """
        # Arrange
        cte_name = "inc_4_measurement"
        table_name = "labevents"
        conditions = [
            ([], ">", 1.5),  # Condition with empty itemids - should be skipped
            ([50885], "<", 100.0),  # Valid condition
        ]

        expected_sql = f"""
        {cte_name} AS (
          SELECT DISTINCT subject_id
          FROM {table_name}
          WHERE (itemid IN (50885) AND valuenum < 100.0)
        )"""

        # Act
        generated_sql = mapper._generate_measurement_table_cte(cte_name, table_name, conditions)

        # Assert
        assert normalize_sql(generated_sql) == normalize_sql(expected_sql)
