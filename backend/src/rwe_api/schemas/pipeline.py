"""Pydantic schemas for pipeline endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import (
    LiteratureDocument,
    LiteratureCorpus,
    TrialCriterion,
    TrialFeature,
    TrialSchema,
    VariableMapping,
    FilterExpression,
    FilterSpec,
    CohortRow,
    CohortResult,
    OutcomeRecord,
    AnalysisMetrics,
    ReportBundle,
)


class SearchLitRequest(BaseModel):
    """Request schema for literature search.

    IMPORTANT: This endpoint ONLY accepts a single NCT ID (e.g., NCT03389555).
    It fetches the full clinical trial data from ClinicalTrials.gov API.

    Example:
        {
            "project_id": "my_project",
            "nct_id": "NCT03389555"
        }
    """

    project_id: str = Field(..., description="Project identifier")
    nct_id: str = Field(
        ...,
        description="ClinicalTrials.gov NCT ID (format: NCT followed by 8 digits, e.g., NCT03389555)",
        pattern=r"^NCT\d{8}$",
        examples=["NCT03389555", "NCT04280705"]
    )


class ParseTrialsRequest(BaseModel):
    """Request schema for trial parsing."""

    project_id: str = Field(..., description="Project identifier")
    llm_provider: str = Field("synthetic-llm", description="LLM provider")
    prompt_template: str = Field("default-trial-prompt.txt", description="Prompt template")
    impl: str | None = Field(None, description="Implementation override")


class MapToEHRRequest(BaseModel):
    """Request schema for EHR mapping."""

    project_id: str = Field(..., description="Project identifier")
    ehr_source: str = Field("mimic", description="EHR data source")
    dictionary: str | None = Field(None, description="Variable dictionary path")
    output_format: Literal["json", "sql"] = Field("json", description="Output format")
    impl: str | None = Field(None, description="Implementation override")


class FilterCohortRequest(BaseModel):
    """Request schema for cohort filtering."""

    project_id: str = Field(..., description="Project identifier")
    input_uri: str = Field("duckdb:///synthetic.duckdb", description="Input database URI")
    sample_size: int | None = Field(None, description="Sample size limit")
    dry_run: bool = Field(False, description="Dry run mode")
    impl: str | None = Field(None, description="Implementation override")


class AnalyzeRequest(BaseModel):
    """Request schema for outcome analysis."""

    project_id: str = Field(..., description="Project identifier")
    treatment_column: str = Field("on_arnI", description="Treatment column name")
    outcome_column: str = Field("mortality_30d", description="Outcome column name")
    estimators: list[str] = Field(..., description="Estimator methods to use")
    impl: str | None = Field(None, description="Implementation override")


class WriteReportRequest(BaseModel):
    """Request schema for report generation."""

    project_id: str = Field(..., description="Project identifier")
    template: str = Field(..., description="Report template path")
    format: Literal["markdown", "pdf"] = Field("markdown", description="Output format")
    hil_review: bool = Field(False, description="Enable human-in-the-loop review")
    impl: str | None = Field(None, description="Implementation override")


class StimulaRequest(BaseModel):
    """Request schema for what-if simulation."""

    project_id: str = Field(..., description="Project identifier")
    vary: list[str] | None = Field(None, description="Variation specifications")
    max_variations: int = Field(3, description="Maximum variations per key")
    subject_id: str | None = Field(None, description="Subject to focus on")


class RunAllRequest(BaseModel):
    """Request schema for full pipeline execution."""

    project_id: str = Field(..., description="Project identifier")
    disease_code: str = Field(..., description="Disease code")
    keywords: list[str] = Field(..., description="Search keywords")
    sources: list[str] = Field(..., description="Data sources")
    max_records: int = Field(5, description="Maximum literature records")
    require_full_text: bool = Field(False, description="Require full text")
    llm_provider: str = Field("synthetic-llm", description="LLM provider")
    prompt_template: str = Field("default-trial-prompt.txt", description="Prompt template")
    ehr_source: str = Field("mimic", description="EHR source")
    dictionary: str | None = Field(None, description="Variable dictionary path")
    filters_format: Literal["json", "sql"] = Field("json", description="Filter format")
    input_uri: str = Field("duckdb:///synthetic.duckdb", description="Input database URI")
    sample_size: int | None = Field(None, description="Sample size")
    treatment_column: str = Field("on_arnI", description="Treatment column")
    outcome_column: str = Field("mortality_30d", description="Outcome column")
    estimators: list[str] = Field(..., description="Estimator methods")
    template: str = Field(..., description="Report template path")
    report_format: Literal["markdown", "pdf"] = Field("markdown", description="Report format")
    impl_overrides: dict[str, str] | None = Field(None, description="Implementation overrides")


class PipelineResponse(BaseModel):
    """Generic response schema for pipeline operations."""

    status: Literal["success", "error", "running"] = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    data: dict[str, Any] | None = Field(None, description="Response data")
    error: str | None = Field(None, description="Error message if failed")


# ------------------------------------------------------------------------------
# Stage-specific Response Models
# ------------------------------------------------------------------------------


class SearchLitResponse(BaseModel):
    """Response for literature search stage."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    corpus: LiteratureCorpus | None = Field(None, description="Literature corpus")
    document_count: int = Field(..., description="Number of documents retrieved")
    error: str | None = Field(None, description="Error message if failed")


class ParseTrialsResponse(BaseModel):
    """Response for trial parsing stage."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    schema: TrialSchema | None = Field(None, description="Trial schema")
    inclusion_count: int = Field(..., description="Number of inclusion criteria")
    exclusion_count: int = Field(..., description="Number of exclusion criteria")
    feature_count: int = Field(..., description="Number of features")
    error: str | None = Field(None, description="Error message if failed")


class MapToEHRResponse(BaseModel):
    """Response for EHR mapping stage."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    filter_spec: FilterSpec | None = Field(None, description="Filter specification")
    variable_map_count: int = Field(..., description="Number of mapped variables")
    inclusion_filters_count: int = Field(..., description="Number of inclusion filters")
    exclusion_filters_count: int = Field(..., description="Number of exclusion filters")
    error: str | None = Field(None, description="Error message if failed")


class FilterCohortResponse(BaseModel):
    """Response for cohort filtering stage."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    cohort: CohortResult | None = Field(None, description="Cohort result")
    total_subjects: int = Field(..., description="Total number of subjects")
    summary: dict[str, Any] = Field(default_factory=dict, description="Cohort summary")
    error: str | None = Field(None, description="Error message if failed")


class AnalyzeResponse(BaseModel):
    """Response for outcome analysis stage."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    analysis: AnalysisMetrics | None = Field(None, description="Analysis results")
    outcome_count: int = Field(..., description="Number of outcome records")
    metrics_summary: dict[str, Any] = Field(
        default_factory=dict, description="Summary metrics"
    )
    error: str | None = Field(None, description="Error message if failed")


class WriteReportResponse(BaseModel):
    """Response for report generation stage."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    report_path: str | None = Field(None, description="Path to generated report")
    report_body_length: int = Field(..., description="Length of report body")
    figure_count: int = Field(..., description="Number of figures")
    error: str | None = Field(None, description="Error message if failed")


class StimulaResponse(BaseModel):
    """Response for what-if simulation."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    scenario_count: int = Field(..., description="Number of scenarios")
    baseline_subjects: int = Field(..., description="Baseline subject count")
    scenarios: list[dict[str, Any]] = Field(
        default_factory=list, description="Scenario results"
    )
    error: str | None = Field(None, description="Error message if failed")


class RunAllResponse(BaseModel):
    """Response for full pipeline execution."""

    status: Literal["success", "error", "running"] = Field(
        ..., description="Operation status"
    )
    message: str = Field(..., description="Status message")
    stages: dict[str, Any] = Field(
        default_factory=dict, description="Results from each stage"
    )
    error: str | None = Field(None, description="Error message if failed")


# ClinicalTrials.gov API Schemas
class CTSearchRequest(BaseModel):
    """Request schema for ClinicalTrials.gov search."""

    query: str | None = Field(None, description="Free-text search query")
    condition: str | None = Field(None, description="Medical condition")
    intervention: str | None = Field(None, description="Intervention/treatment")
    status: list[str] | None = Field(None, description="Trial status filter")
    phase: list[str] | None = Field(None, description="Trial phase filter")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")


class CTSearchResponse(BaseModel):
    """Response schema for ClinicalTrials.gov search."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str | None = Field(None, description="Status message")
    studies: list[dict[str, Any]] = Field(default_factory=list, description="Trial summaries")
    total_count: int = Field(0, description="Total number of matching trials")
    error: str | None = Field(None, description="Error message if failed")


class CTDetailResponse(BaseModel):
    """Response schema for ClinicalTrials.gov trial details."""

    status: Literal["success", "error"] = Field(..., description="Operation status")
    message: str | None = Field(None, description="Status message")
    study: dict[str, Any] | None = Field(None, description="Complete trial details")
    error: str | None = Field(None, description="Error message if failed")



# ============================================================================
# TRIALIST AGENT SCHEMAS
# ============================================================================


class TrialistRunRequest(BaseModel):
    """Request schema for complete Trialist workflow."""

    project_id: str = Field(..., description="Project identifier")
    nct_id: str = Field(
        ...,
        description="ClinicalTrials.gov NCT ID (format: NCT followed by 8 digits)",
        pattern=r"^NCT\d{8}$",
        examples=["NCT03389555", "NCT04280705"]
    )
    fetch_papers: bool = Field(
        True,
        description="Whether to fetch full-text papers from PMC"
    )
    generate_sql: bool = Field(
        True,
        description="Whether to generate MIMIC-IV SQL query"
    )


class RelatedPaper(BaseModel):
    """Schema for a related research paper."""

    pmid: str | None = Field(None, description="PubMed ID")
    pmcid: str | None = Field(None, description="PubMed Central ID")
    doi: str | None = Field(None, description="Digital Object Identifier")
    status: str = Field(..., description="Fetch status (full_text_retrieved, not_in_pmc, error)")
    full_text_preview: str | None = Field(None, description="First 500 characters of markdown text")
    url: str | None = Field(None, description="URL to paper")


class TrialistRunResponse(BaseModel):
    """Response schema for complete Trialist workflow."""

    status: str = Field(..., description="Status of the workflow (success, partial, error)")
    message: str = Field(..., description="Human-readable message")
    nct_id: str = Field(..., description="NCT ID processed")

    # Trial data
    trial_data: dict[str, Any] = Field(..., description="Basic trial information from ClinicalTrials.gov")

    # Parsed schema
    parsed_schema: dict[str, Any] | None = Field(None, description="Enhanced trial schema with OMOP concepts")

    # EHR mapping
    ehr_mapping: dict[str, Any] | None = Field(None, description="MIMIC-IV mapping with generated SQL")

    # Related papers
    related_papers: list[RelatedPaper] = Field(default_factory=list, description="List of related research papers")

    # Execution metadata
    execution_time_ms: float = Field(..., description="Total execution time in milliseconds")
    stages_completed: list[str] = Field(default_factory=list, description="List of completed stages")

