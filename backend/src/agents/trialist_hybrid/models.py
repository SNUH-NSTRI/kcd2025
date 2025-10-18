"""
Pydantic models for Trialist Hybrid 3-Stage Pipeline.

Models handle structured data flow across stages:
- Stage 1: Raw criteria -> CriterionEntity
- Stage 2: CriterionEntity -> MappingOutput
- Stage 3: MappingOutput -> ValidationResult
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class TemporalConstraint(BaseModel):
    """Represents time-based constraints (e.g., 'within 6 months', 'before admission')."""

    operator: Literal["within_last", "before", "after", "between"] = Field(
        description="Temporal operator type"
    )
    value: int = Field(gt=0, description="Numeric value for time constraint")
    unit: Literal["hours", "days", "months", "years"] = Field(
        description="Time unit"
    )
    reference_point: Optional[str] = Field(
        default="admission",
        description="Reference time point (e.g., 'admission', 'discharge', 'now')",
    )

    def to_sql_interval(self) -> str:
        """Convert to SQL INTERVAL format."""
        return f"INTERVAL '{self.value} {self.unit}'"


class CriterionEntity(BaseModel):
    """
    Represents a single clinical trial criterion entity.

    Handles edge cases:
    - Negation: "NOT diabetic"
    - Temporal: "within 6 months"
    - Complex: AND/OR via sub_criteria
    - Value assumptions: "adult" -> age >= 18
    """

    id: str = Field(description="Unique identifier (e.g., 'inc_001')")
    text: str = Field(description="Original criterion text (preserved)")
    entity_type: Literal[
        "demographic", "condition", "procedure", "measurement", "medication"
    ] = Field(description="Domain classification")
    attribute: str = Field(
        description="Specific attribute (e.g., 'age', 'lactate', 'diagnosis')"
    )
    operator: Optional[str] = Field(
        default=None, description="Comparison operator (>, <, >=, <=, ==, !=, IN)"
    )
    value: Optional[str] = Field(
        default=None, description="Value to compare against (numeric or text)"
    )
    unit: Optional[str] = Field(
        default=None, description="Unit of measurement (years, mmHg, mmol/L, etc.)"
    )
    negation: bool = Field(
        default=False, description="True if criterion is negated (NOT/exclude)"
    )
    temporal_constraint: Optional[TemporalConstraint] = Field(
        default=None, description="Time-based constraint if applicable"
    )
    sub_criteria: Optional[List["CriterionEntity"]] = Field(
        default=None,
        description="Nested criteria for complex conditions (AND/OR logic)",
    )
    assumptions_made: List[str] = Field(
        default_factory=list,
        description="List of assumptions made during extraction (e.g., 'adult' -> 18)",
    )

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: Optional[str]) -> Optional[str]:
        """Ensure operator is valid SQL operator."""
        if v is None:
            return v
        valid_ops = {">", "<", ">=", "<=", "==", "!=", "IN", "NOT IN", "LIKE"}
        if v not in valid_ops:
            raise ValueError(f"Invalid operator: {v}. Must be one of {valid_ops}")
        return v


class ExtractionOutput(BaseModel):
    """Stage 1 output: Structured entities from raw criteria."""

    inclusion: List[CriterionEntity] = Field(
        default_factory=list, description="Inclusion criteria entities"
    )
    exclusion: List[CriterionEntity] = Field(
        default_factory=list, description="Exclusion criteria entities"
    )


class MimicMapping(BaseModel):
    """Represents MIMIC-IV database mapping for a criterion."""

    table: str = Field(description="Primary MIMIC-IV table (e.g., 'hosp.patients')")
    columns: List[str] = Field(
        description="Columns needed from the primary table"
    )
    join_table: Optional[str] = Field(
        default=None, description="Secondary table for joins if needed"
    )
    join_columns: Optional[List[str]] = Field(
        default=None, description="Columns from the join table"
    )
    join_condition: Optional[str] = Field(
        default=None, description="SQL join condition (e.g., 'p.subject_id = a.subject_id')"
    )
    sql_condition: str = Field(
        description="SQL WHERE clause condition (e.g., 'anchor_age > 18')"
    )
    icd_codes: Optional[List[str]] = Field(
        default=None, description="ICD-9/10 codes for diagnosis criteria"
    )
    itemids: Optional[List[int]] = Field(
        default=None, description="MIMIC-IV itemids for lab/vital measurements"
    )

    @field_validator("table", "join_table")
    @classmethod
    def validate_table_format(cls, v: Optional[str]) -> Optional[str]:
        """Ensure table names follow schema.table format."""
        if v is None:
            return v
        if "." not in v:
            raise ValueError(f"Table must be in 'schema.table' format, got: {v}")
        return v


class MappingOutput(BaseModel):
    """Stage 2 output: Entity + MIMIC-IV mapping + confidence."""

    criterion: CriterionEntity = Field(description="Original criterion entity")
    mimic_mapping: MimicMapping = Field(description="MIMIC-IV database mapping")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    reasoning: str = Field(
        description="Explanation for the mapping decision"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Round confidence to 2 decimal places."""
        return round(v, 2)


class ValidationResult(BaseModel):
    """Stage 3 output: Validation status + SQL query."""

    criterion_id: str = Field(description="Reference to original criterion ID")
    validation_status: Literal["passed", "warning", "failed", "needs_review"] = Field(
        description="Validation outcome"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Final confidence after validation adjustments"
    )
    flags: List[str] = Field(
        default_factory=list,
        description="Critical issues (e.g., 'INVALID_SCHEMA', 'LOGIC_ERROR')",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical issues (e.g., 'LOW_CONFIDENCE', 'UNIT_CONVERSION')",
    )
    sql_query: Optional[str] = Field(
        default=None, description="Final SQL query (only if passed/warning)"
    )


class PipelineSummary(BaseModel):
    """Summary statistics for the entire pipeline run."""

    total_criteria: int = Field(description="Total number of criteria processed")

    # Stage 1: Extraction
    stage1_extracted: int = Field(description="Number successfully extracted")
    stage1_extraction_rate: float = Field(ge=0.0, le=1.0, description="Extraction success rate")

    # Stage 2: Mapping
    stage2_mapped: int = Field(description="Number successfully mapped")
    stage2_mapping_rate: float = Field(ge=0.0, le=1.0, description="Mapping success rate")

    # Stage 3: Validation
    stage3_passed: int = Field(description="Number that passed validation")
    stage3_warning: int = Field(description="Number with warnings")
    stage3_needs_review: int = Field(description="Number requiring manual review")
    stage3_failed: int = Field(description="Number that failed validation")
    stage3_validation_rate: float = Field(ge=0.0, le=1.0, description="Validation success rate (passed+warning)")

    avg_confidence: float = Field(
        ge=0.0, le=1.0, description="Average confidence score across all criteria"
    )
    execution_time_seconds: Optional[float] = Field(
        default=None, description="Total pipeline execution time"
    )


class PipelineOutput(BaseModel):
    """Complete pipeline output with all stages."""

    extraction: ExtractionOutput = Field(description="Stage 1 extraction results")
    mappings: List[MappingOutput] = Field(description="Stage 2 mapping results")
    validations: List[ValidationResult] = Field(description="Stage 3 validation results")
    summary: PipelineSummary = Field(description="Overall pipeline summary")
