from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, Protocol, Literal

from .context import PipelineContext


# ------------------------------------------------------------------------------
# Search Agent₁ (`search-lit`)
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class SearchLitParams:
    disease_code: str
    keywords: Sequence[str]
    sources: Sequence[str]
    max_records: int
    api_keys: Mapping[str, str] | None = None
    require_full_text: bool = False
    fetch_papers: bool = False


@dataclass(frozen=True)
class LiteratureDocument:
    source: str
    identifier: str
    title: str
    abstract: str | None
    full_text: str | None
    fetched_at: dt.datetime
    url: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class LiteratureCorpus:
    schema_version: str
    documents: Sequence[LiteratureDocument]


class LiteratureFetcher(Protocol):
    def run(self, params: SearchLitParams, ctx: PipelineContext) -> LiteratureCorpus: ...


# ------------------------------------------------------------------------------
# Parser Agent (`parse-trials`)
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ParseTrialsParams:
    llm_provider: str
    prompt_template: str
    validation_resources: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class NamedEntity:
    """Named entity extracted from trial text."""
    text: str
    type: Literal["concept", "temporal", "value"]
    start: int | None = None
    end: int | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class TrialCriterion:
    id: str
    description: str
    category: str
    kind: str
    value: Mapping[str, Any]
    entities: Sequence[NamedEntity] | None = None  # NER 정보


@dataclass(frozen=True)
class TrialFeature:
    name: str
    source: str
    unit: str | None
    time_window: tuple[int, int] | None
    metadata: Mapping[str, Any] | None = None
    entities: Sequence[NamedEntity] | None = None  # NER 정보 (Treatment, Outcomes)


@dataclass(frozen=True)
class TrialSchema:
    schema_version: str
    disease_code: str
    inclusion: Sequence[TrialCriterion]
    exclusion: Sequence[TrialCriterion]
    features: Sequence[TrialFeature]
    provenance: Mapping[str, Any]


class TrialParser(Protocol):
    def run(
        self,
        params: ParseTrialsParams,
        ctx: PipelineContext,
        corpus: LiteratureCorpus,
    ) -> TrialSchema: ...


# ------------------------------------------------------------------------------
# Search Agent₂ (`map-to-ehr`)
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class MapToEHRParams:
    ehr_source: str
    variable_dictionary: Mapping[str, Any]
    output_format: Literal["json", "sql"] = "json"


@dataclass(frozen=True)
class VariableMapping:
    schema_feature: str
    ehr_table: str
    column: str
    concept_id: int | None
    transform: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class FilterExpression:
    criterion_id: str
    expr: Mapping[str, Any]


@dataclass(frozen=True)
class FilterSpec:
    schema_version: str
    ehr_source: str
    variable_map: Sequence[VariableMapping]
    inclusion_filters: Sequence[FilterExpression]
    exclusion_filters: Sequence[FilterExpression]
    lineage: Mapping[str, Any]


class EHRMapper(Protocol):
    def run(
        self,
        params: MapToEHRParams,
        ctx: PipelineContext,
        schema: TrialSchema,
    ) -> FilterSpec: ...


# ------------------------------------------------------------------------------
# Filtering Module (`filter-cohort`)
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class FilterCohortParams:
    input_uri: str
    sample_size: int | None = None
    dry_run: bool = False
    parallelism: int = 1


@dataclass(frozen=True)
class CohortRow:
    subject_id: int | str
    stay_id: int | str | None
    matched_criteria: Sequence[str]
    index_time: dt.datetime
    features: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class CohortResult:
    schema_version: str
    rows: Iterable[CohortRow]
    summary: Mapping[str, Any]


class CohortExtractor(Protocol):
    def run(
        self,
        params: FilterCohortParams,
        ctx: PipelineContext,
        filter_spec: FilterSpec,
    ) -> CohortResult: ...


# ------------------------------------------------------------------------------
# 분석 Agent (`analyze`)
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalyzeParams:
    treatment_column: str
    outcome_column: str
    estimators: Sequence[str]
    feature_config: Mapping[str, Any] | None = None
    log_to: str | None = None


@dataclass(frozen=True)
class StatisticianConfig:
    """Configuration for Statistician plugin statistical methods"""
    # IPTW Configuration
    use_iptw: bool = True
    iptw_clip: tuple[float, float] | None = (0.01, 0.99)  # Weight clipping bounds
    iptw_stabilize: bool = True

    # Cox PH Configuration
    use_cox_ph: bool = True
    time_column: str = "time_to_event"
    event_column: str = "event_occurred"
    cox_alpha: float = 0.05  # Significance level for CI

    # Causal Forest Configuration
    use_causal_forest: bool = True
    cf_n_estimators: int = 100
    cf_min_samples_leaf: int = 10
    cf_max_depth: int | None = None

    # Shapley Configuration
    use_shapley: bool = True
    shapley_max_samples: int = 100  # Max samples for SHAP calculation
    shapley_nperms: int = 10  # Number of permutations

    # General Configuration
    random_state: int = 42
    covariates: Sequence[str] | None = None  # Covariate columns for adjustment


@dataclass(frozen=True)
class OutcomeRecord:
    subject_id: int | str
    propensity: float | None
    ate: float | None
    cate_group: str | None
    predicted_outcome: float | None
    metadata: Mapping[str, Any] | None = None
    # Extended fields for Statistician
    iptw_weight: float | None = None
    hazard_ratio: float | None = None
    survival_prob: float | None = None
    cate_value: float | None = None  # Individual CATE estimate
    shapley_values: Mapping[str, float] | None = None  # Feature contributions


@dataclass(frozen=True)
class AnalysisMetrics:
    schema_version: str
    outcomes: Iterable[OutcomeRecord]
    metrics: Mapping[str, Any]


class OutcomeAnalyzer(Protocol):
    def run(
        self,
        params: AnalyzeParams,
        ctx: PipelineContext,
        cohort: CohortResult,
    ) -> AnalysisMetrics: ...


# ------------------------------------------------------------------------------
# Write Agent (`write-report`)
# ------------------------------------------------------------------------------


@dataclass(frozen=True)
class WriteReportParams:
    template_path: Path
    output_format: Literal["markdown", "pdf"] = "markdown"
    hil_review: bool = False


@dataclass(frozen=True)
class FigureArtifact:
    name: str
    description: str | None
    data: bytes
    media_type: str


@dataclass(frozen=True)
class ReportBundle:
    schema_version: str
    report_body: str
    figures: Sequence[FigureArtifact]
    extra_files: Sequence[tuple[str, bytes]] | None = None


class ReportGenerator(Protocol):
    def run(
        self,
        params: WriteReportParams,
        ctx: PipelineContext,
        analysis: AnalysisMetrics,
    ) -> ReportBundle: ...


__all__ = [
    # Context is re-exported from rwe_cli.context; repeated here for typing tools
    "SearchLitParams",
    "LiteratureDocument",
    "LiteratureCorpus",
    "LiteratureFetcher",
    "ParseTrialsParams",
    "TrialCriterion",
    "TrialFeature",
    "TrialSchema",
    "TrialParser",
    "MapToEHRParams",
    "VariableMapping",
    "FilterExpression",
    "FilterSpec",
    "EHRMapper",
    "FilterCohortParams",
    "CohortRow",
    "CohortResult",
    "CohortExtractor",
    "AnalyzeParams",
    "StatisticianConfig",
    "OutcomeRecord",
    "AnalysisMetrics",
    "OutcomeAnalyzer",
    "WriteReportParams",
    "FigureArtifact",
    "ReportBundle",
    "ReportGenerator",
]
