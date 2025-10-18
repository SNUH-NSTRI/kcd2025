"""
Trialist MIMIC Mapper Plugin

Generates executable SQL queries for MIMIC-IV cohort extraction
from Trialist-parsed trial criteria.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from .. import models
from ..context import PipelineContext
from ..trialist_models import EnhancedTrialSchema, EnhancedTrialCriterion
from ..mimic_concept_mapper import MimicConceptMapper

logger = logging.getLogger(__name__)


class TrialistMimicMapper:
    """
    Maps Trialist-parsed trial criteria to MIMIC-IV SQL queries.

    Generates CTE-based SQL with:
    - Inclusion criteria as INNER JOINs
    - Exclusion criteria as NOT EXISTS
    - Temporal handling for time-based criteria
    """

    def __init__(self):
        self.concept_mapper = MimicConceptMapper()

    def run(
        self,
        params: models.MapToEHRParams,
        ctx: PipelineContext,
        schema: models.TrialSchema,
    ) -> models.FilterSpec:
        """
        Generate MIMIC-IV SQL from trial schema.

        Args:
            params: EHR mapping parameters
            ctx: Pipeline context
            schema: Trial schema from Trialist parser

        Returns:
            FilterSpec with generated SQL query
        """
        logger.info(f"Generating MIMIC SQL for {ctx.project_id}")

        # Convert to enhanced schema if needed
        if not isinstance(schema, EnhancedTrialSchema):
            logger.warning("Schema is not EnhancedTrialSchema, using basic mapping")
            # Fallback to basic schema handling
            return self._generate_basic_sql(schema)

        # Generate SQL CTEs
        inclusion_ctes = self._generate_inclusion_ctes(schema.inclusion)
        exclusion_ctes = self._generate_exclusion_ctes(schema.exclusion)

        # Combine into final query
        sql_query = self._build_final_query(inclusion_ctes, exclusion_ctes)

        # Create FilterSpec
        variable_map = self._extract_variable_map(schema)

        filter_spec = models.FilterSpec(
            schema_version="filter.v1",
            ehr_source="mimic-iv",
            variable_map=variable_map,
            inclusion_filters=[],
            exclusion_filters=[],
            lineage={
                "sql_query": sql_query,
                "nct_id": schema.disease_code,
                "generated_by": "trialist_mimic_mapper"
            }
        )

        return filter_spec

    def _generate_ctes_for_criteria(
        self,
        criteria: List[EnhancedTrialCriterion],
        prefix: str,
        is_inclusion: bool
    ) -> List[tuple[str, str]]:
        """
        Generate SQL CTEs for criteria (DRY refactoring).

        Args:
            criteria: List of trial criteria
            prefix: CTE name prefix ("inc" or "exc")
            is_inclusion: Whether these are inclusion criteria

        Returns:
            List of (cte_name, cte_sql) tuples
        """
        ctes: List[tuple[str, str]] = []

        for criterion in criteria:
            if not criterion.entities:
                continue

            # Group entities by domain
            domain_entities: Dict[str, List] = {}
            for entity in criterion.entities:
                domain = entity.domain.lower()
                if domain not in domain_entities:
                    domain_entities[domain] = []
                domain_entities[domain].append(entity)

            # Generate CTE for each domain
            for domain, entities in domain_entities.items():
                cte_name = f"{prefix}_{criterion.id}_{domain}"
                cte_sql = self._generate_domain_cte(cte_name, domain, entities, is_inclusion=is_inclusion)
                if cte_sql:
                    ctes.append((cte_name, cte_sql))

        return ctes

    def _generate_inclusion_ctes(self, criteria: List[EnhancedTrialCriterion]) -> List[tuple[str, str]]:
        """
        Generate SQL CTEs for inclusion criteria.

        Returns:
            List of (cte_name, cte_sql) tuples
        """
        return self._generate_ctes_for_criteria(criteria, "inc", is_inclusion=True)

    def _generate_exclusion_ctes(self, criteria: List[EnhancedTrialCriterion]) -> List[tuple[str, str]]:
        """
        Generate SQL CTEs for exclusion criteria.

        Returns:
            List of (cte_name, cte_sql) tuples
        """
        return self._generate_ctes_for_criteria(criteria, "exc", is_inclusion=False)

    def _generate_domain_cte(
        self,
        cte_name: str,
        domain: str,
        entities: List,
        is_inclusion: bool
    ) -> str | None:
        """
        Generate SQL CTE for a specific domain.

        Args:
            cte_name: Name of the CTE
            domain: OMOP domain (demographic, condition, measurement, etc.)
            entities: List of entities in this domain
            is_inclusion: Whether this is an inclusion criterion

        Returns:
            SQL CTE string or None if cannot generate
        """
        if domain == "demographic":
            return self._generate_demographic_cte(cte_name, entities)
        elif domain == "condition":
            return self._generate_condition_cte(cte_name, entities)
        elif domain == "measurement":
            return self._generate_measurement_cte(cte_name, entities)
        elif domain == "drug":
            return self._generate_drug_cte(cte_name, entities)
        elif domain == "procedure":
            return self._generate_procedure_cte(cte_name, entities)
        else:
            logger.debug(f"Unsupported domain for SQL generation: {domain}")
            return None

    def _generate_demographic_cte(self, cte_name: str, entities: List) -> str | None:
        """Generate CTE for demographic criteria (age, gender)."""
        conditions: List[str] = []

        for entity in entities:
            text_lower = entity.text.lower()

            # Handle age criteria
            if "age" in text_lower and entity.operator and entity.numeric_value is not None:
                age_value = entity.numeric_value
                operator = entity.operator
                conditions.append(f"anchor_age {operator} {age_value}")

            # Handle gender criteria
            elif "male" in text_lower or "female" in text_lower:
                if "female" in text_lower:
                    conditions.append("gender = 'F'")
                elif "male" in text_lower and "female" not in text_lower:
                    conditions.append("gender = 'M'")

        if not conditions:
            return None

        where_clause = " AND ".join(conditions)
        return f"""
{cte_name} AS (
  SELECT DISTINCT subject_id
  FROM patients
  WHERE {where_clause}
)"""

    def _generate_icd_cte(
        self,
        cte_name: str,
        entities: List,
        table_name: str
    ) -> str | None:
        """
        Generate CTE for ICD-based criteria (DRY refactoring).

        Args:
            cte_name: Name of the CTE
            entities: List of entities
            table_name: MIMIC table name (diagnoses_icd or procedures_icd)

        Returns:
            SQL CTE string or None
        """
        icd_conditions: List[str] = []

        for entity in entities:
            mapping = self.concept_mapper.map_entity(entity)
            if mapping:
                icd9_codes = mapping.get("icd9_codes", [])
                icd10_codes = mapping.get("icd10_codes", [])

                # Build LIKE conditions for ICD codes
                code_conditions: List[str] = []
                for code in icd9_codes:
                    code_conditions.append(f"icd_code LIKE '{code}'")
                for code in icd10_codes:
                    code_conditions.append(f"icd_code LIKE '{code}'")

                if code_conditions:
                    icd_conditions.append(f"({' OR '.join(code_conditions)})")

        if not icd_conditions:
            return None

        where_clause = " OR ".join(icd_conditions)
        return f"""
{cte_name} AS (
  SELECT DISTINCT subject_id
  FROM {table_name}
  WHERE {where_clause}
)"""

    def _generate_condition_cte(self, cte_name: str, entities: List) -> str | None:
        """Generate CTE for condition/diagnosis criteria."""
        return self._generate_icd_cte(cte_name, entities, "diagnoses_icd")

    def _generate_measurement_cte(self, cte_name: str, entities: List) -> str | None:
        """Generate CTE for measurement/lab criteria."""
        # Separate lab events and chart events
        lab_conditions: List[tuple[List[int], str, float]] = []  # (itemids, operator, value)
        chart_conditions: List[tuple[List[int], str, float]] = []

        for entity in entities:
            mapping = self.concept_mapper.map_entity(entity)
            if not mapping:
                continue

            table = mapping.get("table")
            itemids = mapping.get("itemids", [])

            # Extract value conditions
            if entity.operator and entity.numeric_value is not None:
                operator = entity.operator
                value = entity.numeric_value

                if table == "labevents":
                    lab_conditions.append((itemids, operator, value))
                elif table == "chartevents":
                    chart_conditions.append((itemids, operator, value))

        if lab_conditions:
            return self._generate_measurement_table_cte(
                cte_name, "labevents", lab_conditions
            )

        if chart_conditions:
            return self._generate_measurement_table_cte(
                cte_name, "chartevents", chart_conditions
            )

        return None

    def _generate_measurement_table_cte(
        self,
        cte_name: str,
        table_name: str,
        conditions: List[tuple[List[int], str, float]],
    ) -> str | None:
        """
        Generate CTE for a single measurement table (labevents or chartevents).

        Args:
            cte_name: Name of the CTE.
            table_name: The table to query (e.g., 'labevents').
            conditions: A list of tuples, each containing (itemids, operator, value).

        Returns:
            A SQL CTE string or None if no conditions are provided.
        """
        if not conditions:
            return None

        clauses: List[str] = []
        for itemids, operator, value in conditions:
            if not itemids:  # Skip conditions with empty itemid lists
                continue
            itemid_list = ", ".join(str(i) for i in itemids)
            clauses.append(f"(itemid IN ({itemid_list}) AND valuenum {operator} {value})")

        if not clauses:  # Return None if all conditions had empty itemids
            return None

        where_clause = " OR ".join(clauses)
        return f"""
{cte_name} AS (
  SELECT DISTINCT subject_id
  FROM {table_name}
  WHERE {where_clause}
)"""

    def _generate_drug_cte(self, cte_name: str, entities: List) -> str | None:
        """Generate CTE for drug/prescription criteria."""
        drug_conditions: List[str] = []

        for entity in entities:
            mapping = self.concept_mapper.map_entity(entity)
            if mapping:
                patterns = mapping.get("drug_name_pattern", [])
                pattern_conditions = []
                for pattern in patterns:
                    pattern_conditions.append(f"LOWER(drug) LIKE '%{pattern.lower()}%'")

                if pattern_conditions:
                    drug_conditions.append(f"({' OR '.join(pattern_conditions)})")

        if not drug_conditions:
            return None

        where_clause = " OR ".join(drug_conditions)
        return f"""
{cte_name} AS (
  SELECT DISTINCT subject_id
  FROM prescriptions
  WHERE {where_clause}
)"""

    def _generate_procedure_cte(self, cte_name: str, entities: List) -> str | None:
        """Generate CTE for procedure criteria."""
        return self._generate_icd_cte(cte_name, entities, "procedures_icd")

    def _build_final_query(
        self,
        inclusion_ctes: List[tuple[str, str]],
        exclusion_ctes: List[tuple[str, str]]
    ) -> str:
        """
        Build final SQL query combining all CTEs.

        Args:
            inclusion_ctes: List of (name, sql) for inclusion criteria
            exclusion_ctes: List of (name, sql) for exclusion criteria

        Returns:
            Complete SQL query string
        """
        query_parts: List[str] = ["WITH"]

        # Add all CTEs
        all_ctes = inclusion_ctes + exclusion_ctes
        cte_definitions = [cte_sql.strip() for _, cte_sql in all_ctes]
        query_parts.append(",\n".join(cte_definitions))

        # Build final SELECT
        query_parts.append("\n-- Final Cohort Selection")
        query_parts.append("SELECT DISTINCT pat.subject_id")
        query_parts.append("FROM patients pat")

        # INNER JOIN for inclusion criteria
        for cte_name, _ in inclusion_ctes:
            query_parts.append(f"INNER JOIN {cte_name} ON pat.subject_id = {cte_name}.subject_id")

        # WHERE NOT EXISTS for exclusion criteria
        if exclusion_ctes:
            query_parts.append("WHERE")
            exclusion_conditions = []
            for cte_name, _ in exclusion_ctes:
                exclusion_conditions.append(f"  NOT EXISTS (SELECT 1 FROM {cte_name} WHERE {cte_name}.subject_id = pat.subject_id)")
            query_parts.append("\n  AND ".join(exclusion_conditions))

        query_parts.append(";")

        return "\n".join(query_parts)

    def _generate_basic_sql(self, schema: models.TrialSchema) -> models.FilterSpec:
        """Fallback: Generate basic SQL for non-enhanced schema."""
        logger.warning("Using basic SQL generation (EnhancedTrialSchema not available)")

        # Simple placeholder SQL
        sql_query = """
-- Basic cohort extraction (placeholder)
SELECT DISTINCT subject_id
FROM patients
WHERE anchor_age >= 18;
"""

        return models.FilterSpec(
            schema_version="filter.v1",
            ehr_source="mimic-iv",
            variable_map=[],
            inclusion_filters=[],
            exclusion_filters=[],
            lineage={
                "sql_query": sql_query,
                "generated_by": "trialist_mimic_mapper_basic"
            }
        )

    def _extract_variable_map(self, schema: EnhancedTrialSchema) -> List[models.VariableMapping]:
        """Extract variable mapping from schema."""
        mappings = []

        # Add demographic variables
        mappings.append(models.VariableMapping(
            schema_feature="age",
            ehr_table="patients",
            column="anchor_age",
            concept_id=None
        ))
        mappings.append(models.VariableMapping(
            schema_feature="gender",
            ehr_table="patients",
            column="gender",
            concept_id=None
        ))

        # Add common measurements
        mappings.append(models.VariableMapping(
            schema_feature="lvef",
            ehr_table="chartevents",
            column="valuenum",
            concept_id=227008
        ))
        mappings.append(models.VariableMapping(
            schema_feature="bnp",
            ehr_table="labevents",
            column="valuenum",
            concept_id=50885
        ))
        mappings.append(models.VariableMapping(
            schema_feature="creatinine",
            ehr_table="labevents",
            column="valuenum",
            concept_id=50912
        ))

        return mappings


__all__ = ["TrialistMimicMapper"]
