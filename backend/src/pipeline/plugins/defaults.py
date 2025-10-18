from __future__ import annotations

import base64
import datetime as dt
import math
import random
from typing import Any, Mapping

from ..context import PipelineContext
from .. import models


class SyntheticLiteratureFetcher:
    """Generate a synthetic literature corpus for offline development."""

    def run(
        self, params: models.SearchLitParams, ctx: PipelineContext
    ) -> models.LiteratureCorpus:
        if params.max_records < 1:
            raise ValueError("max_records must be at least 1")
        if not params.sources:
            raise ValueError("at least one source identifier is required")
        if any(not kw.strip() for kw in params.keywords):
            raise ValueError("keywords must not contain empty strings")

        rng = random.Random(hash((ctx.project_id, params.disease_code)) & 0xFFFFFFFF)
        now = dt.datetime.now(dt.timezone.utc)

        doc_count = min(params.max_records, max(3, len(params.keywords) + 2))
        documents: list[models.LiteratureDocument] = []
        for idx in range(doc_count):
            source = params.sources[idx % len(params.sources)]
            identifier = f"{source.upper()}-{1000 + idx}"
            title_keywords = ", ".join(params.keywords[:3]) or params.disease_code
            documents.append(
                models.LiteratureDocument(
                    source=source,
                    identifier=identifier,
                    title=f"Synthetic clinical study {idx + 1} for {params.disease_code}",
                    abstract=(
                        f"This synthetic abstract summarises a randomized study related to "
                        f"{params.disease_code}. Key terms: {title_keywords}."
                    ),
                    full_text=(
                        "This generated document emulates the structure of a clinical trial "
                        "report, including eligibility criteria, intervention details, and "
                        "primary outcomes."
                    ),
                    fetched_at=now - dt.timedelta(minutes=rng.randint(0, 120)),
                    url=f"https://example.org/{identifier.lower()}",
                    metadata={
                        "relevance_score": round(rng.uniform(0.6, 0.99), 3),
                        "keywords": list(params.keywords),
                        "disease_code": params.disease_code,
                    },
                )
            )

        return models.LiteratureCorpus(schema_version="lit.v1", documents=documents)


class SyntheticTrialParser:
    """Derive a trial schema from the synthetic literature corpus."""

    def run(
        self,
        params: models.ParseTrialsParams,
        ctx: PipelineContext,
        corpus: models.LiteratureCorpus,
    ) -> models.TrialSchema:
        if not corpus.documents:
            raise ValueError("corpus must contain at least one document")

        rng = random.Random(hash((ctx.project_id, params.llm_provider)) & 0xFFFFFFFF)
        now = dt.datetime.now(dt.timezone.utc)
        disease_code = corpus.documents[0].metadata.get("disease_code") if corpus.documents[0].metadata else ctx.project_id
        disease_code = str(disease_code or ctx.project_id)

        inclusion = [
            models.TrialCriterion(
                id="inc_age",
                description="Age between 45 and 85 years at index time",
                category="inclusion",
                kind="demographic",
                value={"field": "age", "op": "between", "min": 45, "max": 85},
            ),
            models.TrialCriterion(
                id="inc_lvef",
                description="Left ventricular ejection fraction below 40%",
                category="inclusion",
                kind="clinical",
                value={"field": "lvef", "op": "<", "value": 40.0},
            ),
        ]
        exclusion = [
            models.TrialCriterion(
                id="exc_renal",
                description="Severe renal dysfunction (eGFR < 30 mL/min/1.73m2)",
                category="exclusion",
                kind="clinical",
                value={"field": "egfr", "op": "<", "value": 30.0},
            ),
            models.TrialCriterion(
                id="exc_recent_mi",
                description="Myocardial infarction within the last 30 days",
                category="exclusion",
                kind="clinical",
                value={"field": "mi_within_days", "op": "<=", "value": 30},
            ),
        ]

        features = [
            models.TrialFeature(
                name="lvef",
                source="echodata",
                unit="percent",
                time_window=(-24, 0),
                metadata={"aggregation": "latest"},
            ),
            models.TrialFeature(
                name="bnp",
                source="labevents",
                unit="pg/mL",
                time_window=(-24, 0),
                metadata={"concept": "BNP"},
            ),
            models.TrialFeature(
                name="age",
                source="patients",
                unit="years",
                time_window=None,
                metadata=None,
            ),
            models.TrialFeature(
                name="on_arnI",
                source="prescriptions",
                unit=None,
                time_window=(-7, 0),
                metadata={"drug_class": "ARNI"},
            ),
        ]

        provenance = {
            "schema_version": "schema.v1",
            "generated_at": now.isoformat(),
            "llm_provider": params.llm_provider,
            "prompt_template": params.prompt_template,
            "documents": [doc.identifier for doc in corpus.documents],
            "validation": params.validation_resources or {},
            "confidence": round(rng.uniform(0.7, 0.95), 2),
        }

        return models.TrialSchema(
            schema_version="schema.v1",
            disease_code=disease_code,
            inclusion=inclusion,
            exclusion=exclusion,
            features=features,
            provenance=provenance,
        )


class SyntheticEHRMapper:
    """Project trial schema definitions onto an EHR feature dictionary."""

    def run(
        self,
        params: models.MapToEHRParams,
        ctx: PipelineContext,
        schema: models.TrialSchema,
    ) -> models.FilterSpec:
        if not schema.inclusion or not schema.exclusion:
            raise ValueError("schema must contain inclusion and exclusion criteria")

        tables = params.variable_dictionary.get("tables", {}) if params.variable_dictionary else {}
        mappings = params.variable_dictionary.get("mappings", {}) if params.variable_dictionary else {}
        now = dt.datetime.now(dt.timezone.utc)

        variable_map: list[models.VariableMapping] = []
        for feature in schema.features:
            table_meta: Mapping[str, Any] = tables.get(feature.source, {})
            columns_meta: Mapping[str, Any] = table_meta.get("columns", {}) if isinstance(table_meta, Mapping) else {}
            column = next(iter(columns_meta.keys()), feature.name)
            concept = mappings.get(feature.metadata.get("concept") if feature.metadata else feature.name)
            concept_id = None
            if isinstance(concept, Mapping) and "concept_id" in concept:
                concept_id = concept["concept_id"]

            variable_map.append(
                models.VariableMapping(
                    schema_feature=feature.name,
                    ehr_table=feature.source,
                    column=column,
                    concept_id=concept_id,
                    transform={"unit": feature.unit} if feature.unit else None,
                )
            )

        inclusion_filters = [
            models.FilterExpression(
                criterion_id=criterion.id,
                expr={
                    "table": variable_map[0].ehr_table if variable_map else "patients",
                    "field": criterion.value.get("field", criterion.id),
                    "op": criterion.value.get("op", "="),
                    "value": criterion.value.get("value")
                    if "value" in criterion.value
                    else {
                        "min": criterion.value.get("min"),
                        "max": criterion.value.get("max"),
                    },
                },
            )
            for criterion in schema.inclusion
        ]

        exclusion_filters = [
            models.FilterExpression(
                criterion_id=criterion.id,
                expr={
                    "table": variable_map[0].ehr_table if variable_map else "patients",
                    "field": criterion.value.get("field", criterion.id),
                    "op": criterion.value.get("op", "="),
                    "value": criterion.value.get("value"),
                },
            )
            for criterion in schema.exclusion
        ]

        lineage = {
            "schema_version": schema.schema_version,
            "generated_at": now.isoformat(),
            "mapper_impl": "synthetic",
            "ehr_source": params.ehr_source,
        }

        return models.FilterSpec(
            schema_version="filters.v1",
            ehr_source=params.ehr_source,
            variable_map=variable_map,
            inclusion_filters=inclusion_filters,
            exclusion_filters=exclusion_filters,
            lineage=lineage,
        )


def _sample_feature_value(name: str, rng: random.Random) -> Any:
    key = name.lower()
    if "age" in key:
        return rng.randint(50, 85)
    if "lvef" in key:
        return round(rng.uniform(20, 45), 1)
    if "bnp" in key:
        return round(math.exp(rng.uniform(5, 8)), 1)
    if key.startswith("on_"):
        return rng.random() > 0.4
    if "creatinine" in key:
        return round(rng.uniform(0.6, 2.5), 2)
    return round(rng.uniform(0, 1), 3)


class SyntheticCohortExtractor:
    """Generate a synthetic cohort that satisfies the filter specification."""

    def run(
        self,
        params: models.FilterCohortParams,
        ctx: PipelineContext,
        filter_spec: models.FilterSpec,
    ) -> models.CohortResult:
        if params.dry_run:
            summary = {
                "total_subjects": 0,
                "exclusion_counts": {
                    expr.criterion_id: 0 for expr in filter_spec.exclusion_filters
                },
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "dry_run": True,
            }
            return models.CohortResult(schema_version="cohort.v1", rows=(), summary=summary)

        rng = random.Random(hash((ctx.project_id, filter_spec.ehr_source)) & 0xFFFFFFFF)
        row_count = params.sample_size or 50

        rows: list[models.CohortRow] = []
        base_time = dt.datetime.now(dt.timezone.utc)

        for idx in range(row_count):
            subject_id = f"{ctx.project_id}-{1000 + idx}"
            stay_id = f"{ctx.project_id}-stay-{idx}" if rng.random() > 0.2 else None
            matched = [
                expr.criterion_id
                for expr in filter_spec.inclusion_filters
                if rng.random() > 0.1
            ]
            if not matched and filter_spec.inclusion_filters:
                matched = [filter_spec.inclusion_filters[0].criterion_id]

            features = {
                mapping.schema_feature: _sample_feature_value(
                    mapping.schema_feature, rng
                )
                for mapping in filter_spec.variable_map
            }

            rows.append(
                models.CohortRow(
                    subject_id=subject_id,
                    stay_id=stay_id,
                    matched_criteria=matched,
                    index_time=base_time - dt.timedelta(days=rng.randint(0, 365)),
                    features=features,
                )
            )

        summary = {
            "total_subjects": len(rows),
            "exclusion_counts": {
                expr.criterion_id: rng.randint(0, 5)
                for expr in filter_spec.exclusion_filters
            },
            "generated_at": base_time.isoformat(),
        }

        return models.CohortResult(schema_version="cohort.v1", rows=rows, summary=summary)


class SyntheticOutcomeAnalyzer:
    """Produce synthetic counterfactual metrics for the cohort."""

    def run(
        self,
        params: models.AnalyzeParams,
        ctx: PipelineContext,
        cohort: models.CohortResult,
    ) -> models.AnalysisMetrics:
        if not params.estimators:
            raise ValueError("at least one estimator must be provided")

        cohort_rows = list(cohort.rows)
        if not cohort_rows:
            raise ValueError("cohort must contain at least one row")

        rng = random.Random(hash((ctx.project_id, params.treatment_column)) & 0xFFFFFFFF)
        outcomes: list[models.OutcomeRecord] = []
        ate_values: list[float] = []

        for row in cohort_rows:
            propensity = round(rng.uniform(0.1, 0.9), 3)
            ate = round(rng.uniform(-0.05, 0.15), 3)
            cate_group = "benefit" if ate > 0.05 else ("harm" if ate < -0.02 else "neutral")
            predicted_outcome = round(rng.uniform(0.1, 0.4), 3)
            ate_values.append(ate)

            outcomes.append(
                models.OutcomeRecord(
                    subject_id=row.subject_id,
                    propensity=propensity,
                    ate=ate,
                    cate_group=cate_group,
                    predicted_outcome=predicted_outcome,
                    metadata={
                        "matched_criteria": list(row.matched_criteria),
                        "feature_snapshot": dict(row.features or {}),
                    },
                )
            )

        metrics = {
            "schema_version": "analysis.v1",
            "estimators": list(params.estimators),
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "summary": {
                "n_subjects": len(outcomes),
                "mean_ate": round(sum(ate_values) / len(ate_values), 4),
                "positive_response_rate": round(
                    sum(1 for ate in ate_values if ate > 0.05) / len(ate_values), 4
                ),
            },
        }

        return models.AnalysisMetrics(
            schema_version="analysis.v1",
            outcomes=outcomes,
            metrics=metrics,
        )


_ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADjgF/qSb9lQAAAABJRU5ErkJggg=="
)


class SyntheticReportGenerator:
    """Render a lightweight Markdown report and placeholder figure."""

    def run(
        self,
        params: models.WriteReportParams,
        ctx: PipelineContext,
        analysis: models.AnalysisMetrics,
    ) -> models.ReportBundle:
        if not params.template_path.exists():
            raise FileNotFoundError(params.template_path)

        template_text = params.template_path.read_text(encoding="utf-8")
        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
        metrics = analysis.metrics

        preview_rows = list(analysis.outcomes)
        preview_table_lines: list[str] = []
        header = "| Subject | Propensity | ATE | Group | Predicted |"
        separator = "| --- | --- | --- | --- | --- |"
        preview_table_lines.extend([header, separator])
        for row in preview_rows[: min(5, len(preview_rows))]:
            preview_table_lines.append(
                f"| {row.subject_id} | {row.propensity} | {row.ate} | "
                f"{row.cate_group} | {row.predicted_outcome} |"
            )

        report_context = {
            "project_id": ctx.project_id,
            "generated_at": now_iso,
            "metrics": metrics,
            "table": "\n".join(preview_table_lines),
            "hil_enabled": ctx.hil_enabled,
        }

        try:
            report_body = template_text.format(**report_context)
        except KeyError:
            # Fallback to simple append if template does not expose placeholders.
            report_body = (
                f"# RWE Report for {ctx.project_id}\n\nGenerated at {now_iso}.\n\n"
                f"## Metrics\n\n```\n{metrics}\n```\n\n## Preview\n\n"
                + "\n".join(preview_table_lines)
            )

        figures = [
            models.FigureArtifact(
                name="synthetic-outcome-curve",
                description="Placeholder figure for outcome distribution.",
                data=_ONE_BY_ONE_PNG,
                media_type="image/png",
            )
        ]

        return models.ReportBundle(
            schema_version="report.v1",
            report_body=report_body,
            figures=figures,
            extra_files=None,
        )


__all__ = [
    "SyntheticLiteratureFetcher",
    "SyntheticTrialParser",
    "SyntheticEHRMapper",
    "SyntheticCohortExtractor",
    "SyntheticOutcomeAnalyzer",
    "SyntheticReportGenerator",
]
