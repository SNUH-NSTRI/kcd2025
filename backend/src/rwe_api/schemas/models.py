"""Pydantic models matching CLI dataclass specifications from documents/cli_modules.md."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# Search Agent₁ (`search-lit`)
# ------------------------------------------------------------------------------


class LiteratureDocument(BaseModel):
    """Literature document from search results."""

    source: str = Field(..., description="Source identifier (e.g., 'clinicaltrials')")
    identifier: str = Field(..., description="Unique identifier (NCT ID, PMID, etc.)")
    title: str = Field(..., description="Document title")
    abstract: str | None = Field(None, description="Document abstract")
    full_text: str | None = Field(None, description="Full text content")
    fetched_at: datetime = Field(..., description="Fetch timestamp (UTC)")
    url: str | None = Field(None, description="Document URL")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class LiteratureCorpus(BaseModel):
    """Collection of literature documents."""

    schema_version: str = Field(..., description="Schema version (e.g., 'lit.v1')")
    documents: list[LiteratureDocument] = Field(..., description="List of documents")


# ------------------------------------------------------------------------------
# Parser Agent (`parse-trials`)
# ------------------------------------------------------------------------------


class NamedEntity(BaseModel):
    """Named entity extracted from trial text via NER."""

    text: str = Field(..., description="Entity text span")
    type: Literal["concept", "temporal", "value"] = Field(
        ..., description="Entity type: concept (medical terms), temporal (time), value (numbers)"
    )
    start: int | None = Field(None, description="Start character position")
    end: int | None = Field(None, description="End character position")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class TrialCriterion(BaseModel):
    """Trial inclusion or exclusion criterion."""

    id: str = Field(..., description="Unique criterion identifier")
    description: str = Field(..., description="Human-readable description")
    category: str = Field(
        ..., description="Criterion category (demographic, clinical, laboratory, imaging, therapy)"
    )
    kind: str = Field(
        ..., description="Criterion type (threshold, diagnosis, temporal, composite)"
    )
    value: dict[str, Any] = Field(..., description="Criterion value specification")
    entities: list[NamedEntity] | None = Field(
        None, description="Named entities (concept/temporal/value) extracted via NER"
    )


class TrialFeature(BaseModel):
    """Trial feature specification."""

    name: str = Field(..., description="Feature name")
    source: str = Field(..., description="Data source identifier")
    unit: str | None = Field(None, description="Measurement unit")
    time_window: tuple[int, int] | None = Field(
        None, description="Time window in hours (start, end)"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")
    entities: list[NamedEntity] | None = Field(
        None, description="Named entities (concept/temporal/value) for treatments/outcomes"
    )


class TrialSchema(BaseModel):
    """Structured trial schema extracted from literature."""

    schema_version: str = Field(..., description="Schema version (e.g., 'schema.v1')")
    disease_code: str = Field(..., description="Disease or condition code")
    inclusion: list[TrialCriterion] = Field(..., description="Inclusion criteria")
    exclusion: list[TrialCriterion] = Field(..., description="Exclusion criteria")
    features: list[TrialFeature] = Field(..., description="Trial features")
    provenance: dict[str, Any] = Field(
        default_factory=dict, description="Provenance information"
    )


# ------------------------------------------------------------------------------
# Search Agent₂ (`map-to-ehr`)
# ------------------------------------------------------------------------------


class VariableMapping(BaseModel):
    """Mapping between trial schema feature and EHR variable."""

    schema_feature: str = Field(..., description="Trial schema feature name")
    ehr_table: str = Field(..., description="EHR table name")
    column: str = Field(..., description="EHR column name")
    concept_id: int | None = Field(None, description="Concept ID (OMOP, LOINC, etc.)")
    transform: dict[str, Any] | None = Field(
        None, description="Transformation specification"
    )


class FilterExpression(BaseModel):
    """Filter expression for cohort selection."""

    criterion_id: str = Field(..., description="Associated criterion ID")
    expr: dict[str, Any] = Field(
        ..., description="Filter expression (op, field, value)"
    )


class FilterSpec(BaseModel):
    """EHR filter specification."""

    schema_version: str = Field(
        ..., description="Schema version (e.g., 'filters.v1')"
    )
    ehr_source: str = Field(..., description="EHR source identifier")
    variable_map: list[VariableMapping] = Field(..., description="Variable mappings")
    inclusion_filters: list[FilterExpression] = Field(
        ..., description="Inclusion filter expressions"
    )
    exclusion_filters: list[FilterExpression] = Field(
        ..., description="Exclusion filter expressions"
    )
    lineage: dict[str, Any] = Field(
        default_factory=dict, description="Lineage information"
    )


# ------------------------------------------------------------------------------
# Filtering Module (`filter-cohort`)
# ------------------------------------------------------------------------------


class CohortRow(BaseModel):
    """Individual patient row in cohort."""

    subject_id: int | str = Field(..., description="Patient/subject identifier")
    stay_id: int | str | None = Field(None, description="Stay/encounter identifier")
    matched_criteria: list[str] = Field(
        ..., description="List of matched criterion IDs"
    )
    index_time: datetime = Field(..., description="Index time for patient (UTC)")
    features: dict[str, Any] | None = Field(None, description="Patient features")


class CohortResult(BaseModel):
    """Cohort extraction result."""

    schema_version: str = Field(..., description="Schema version (e.g., 'cohort.v1')")
    rows: list[CohortRow] = Field(..., description="Cohort rows")
    summary: dict[str, Any] = Field(..., description="Cohort summary statistics")


# ------------------------------------------------------------------------------
# 분석 Agent (`analyze`)
# ------------------------------------------------------------------------------


class OutcomeRecord(BaseModel):
    """Individual outcome record for a subject."""

    subject_id: int | str = Field(..., description="Patient/subject identifier")
    propensity: float | None = Field(None, description="Propensity score")
    ate: float | None = Field(None, description="Average treatment effect")
    cate_group: str | None = Field(
        None, description="Conditional average treatment effect group"
    )
    predicted_outcome: float | None = Field(None, description="Predicted outcome")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class AnalysisMetrics(BaseModel):
    """Analysis results with metrics."""

    schema_version: str = Field(
        ..., description="Schema version (e.g., 'analysis.v1')"
    )
    outcomes: list[OutcomeRecord] = Field(..., description="Outcome records")
    metrics: dict[str, Any] = Field(..., description="Summary metrics")


# ------------------------------------------------------------------------------
# Write Agent (`write-report`)
# ------------------------------------------------------------------------------


class FigureArtifact(BaseModel):
    """Figure artifact for report."""

    name: str = Field(..., description="Figure name")
    description: str | None = Field(None, description="Figure description")
    data: bytes = Field(..., description="Figure binary data")
    media_type: str = Field(..., description="MIME type (e.g., 'image/png')")


class ReportBundle(BaseModel):
    """Report generation bundle."""

    schema_version: str = Field(..., description="Schema version (e.g., 'report.v1')")
    report_body: str = Field(..., description="Markdown report body")
    figures: list[FigureArtifact] = Field(..., description="Report figures")
    extra_files: list[tuple[str, bytes]] | None = Field(
        None, description="Additional files"
    )


