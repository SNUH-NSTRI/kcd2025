"""Service for pipeline operations, directly using CLI models."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from pipeline import models
from pipeline.utils import (
    load_variable_dictionary,
    stage_path,
    resolve_impl_name,
    STAGE_ALIAS,
    load_config,
    load_corpus_from_disk,
    load_schema_from_disk,
    load_filter_spec_from_disk,
    load_cohort_from_disk,
    load_analysis_from_disk,
    parse_variations,
)
from pipeline.context import create_context
from pipeline.plugins import registry
from pipeline.plugins.datathon_demo import DatathonDemoLoader
from pipeline.plugins.mimic_demo import MimicDemoCohortExtractor
from pipeline.serialization import (
    dataclass_to_dict,
    write_json,
    write_jsonl,
    write_parquet,
    write_text,
    write_binary,
)

import datetime as dt


class PipelineService:
    """Service for executing pipeline stages."""

    def __init__(self, workspace_root: Path, config_path: Path | None = None):
        """Initialize pipeline service.

        Args:
            workspace_root: Root directory for workspace
            config_path: Optional path to configuration file
        """
        self.workspace_root = workspace_root
        self.config_path = config_path or Path("config.yaml")
        self.logger = self._setup_logger()

        # Initialize demo loader if demo mode is enabled
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        self.demo_loader = DatathonDemoLoader(
            fixtures_root=os.getenv("DEMO_FIXTURES_PATH", "data/fixtures/datathon")
        ) if self.demo_mode else None

        if self.demo_mode:
            self.logger.info("🎯 Demo mode enabled - will use pre-prepared fixtures")

    def _setup_logger(self) -> logging.Logger:
        """Setup logger for pipeline operations."""
        logger = logging.getLogger("rwe_api")
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def _create_context(self, project_id: str, hil_enabled: bool = False):
        """Create pipeline context."""
        config = load_config(self.config_path)
        return create_context(
            project_id=project_id,
            workspace=self.workspace_root,
            config=config,
            hil_enabled=hil_enabled,
            logger=self.logger,
        )

    def _get_impl_name(
        self, stage: str, impl_override: str | None, config: dict
    ) -> str:
        """Get implementation name for a stage.

        Args:
            stage: Pipeline stage name (e.g., 'search-lit', 'parse-trials')
            impl_override: Implementation name override (e.g., 'langgraph-search', 'synthetic')
            config: Configuration dictionary

        Returns:
            Implementation name to use
        """
        if impl_override:
            # impl_override는 구현체 이름 (예: 'langgraph-search', 'mimic-demo')
            return impl_override
        return resolve_impl_name(stage, config, {})

    def _is_demo_nct(self, nct_id: str) -> bool:
        """
        Check if the given NCT ID should use demo mode.

        Args:
            nct_id: NCT ID (can be part of project_id)

        Returns:
            True if demo fixtures are available
        """
        if not self.demo_mode or not self.demo_loader:
            return False

        # Extract NCT ID from project_id if needed (e.g., "nct03389555" -> "NCT03389555")
        nct_normalized = nct_id.upper()
        if not nct_normalized.startswith("NCT"):
            nct_normalized = f"NCT{nct_normalized.replace('NCT', '').replace('nct', '')}"

        return self.demo_loader.is_demo_available(nct_normalized)

    async def search_literature(
        self,
        project_id: str,
        nct_id: str,
        fetch_papers: bool = False,
    ) -> models.LiteratureCorpus:
        """Execute literature search stage.

        FIXED BEHAVIOR:
        - Always uses langgraph-search implementation (real ClinicalTrials.gov API)
        - Always searches by NCT ID only
        - Always returns exactly 1 document
        - Never generates synthetic data

        Args:
            project_id: Project identifier
            nct_id: ClinicalTrials.gov NCT ID (e.g., NCT03389555)
            fetch_papers: Whether to fetch full-text papers from PMC (default: False)

        Returns:
            LiteratureCorpus with exactly 1 document from ClinicalTrials.gov
        """
        ctx = self._create_context(project_id)
        config = load_config(self.config_path)
        impl_name = self._get_impl_name("search-lit", None, config)

        # Get implementation from registry (always langgraph-search)
        fetcher = registry.get_literature(impl_name)

        # Create params with FIXED values - always search by NCT ID only
        params = models.SearchLitParams(
            disease_code="",  # Empty - NCT ID search doesn't need disease code
            keywords=[nct_id],  # Single NCT ID
            sources=["clinicaltrials"],  # Always ClinicalTrials.gov
            max_records=1,  # Always 1 document
            api_keys=None,
            require_full_text=False,
            fetch_papers=fetch_papers,  # Pass through fetch_papers flag
        )

        # Execute
        corpus = fetcher.run(params, ctx)

        # Save to workspace (JSON format - our standard)
        out_dir = stage_path(ctx, "lit")

        # Save corpus as JSON (our standard format)
        write_json(
            out_dir / "corpus.json",
            {
                "schema_version": corpus.schema_version,
                "documents": [dataclass_to_dict(doc) for doc in corpus.documents],
                "document_count": len(corpus.documents),
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            },
        )

        # Also save manifest for backward compatibility
        write_json(
            out_dir / "manifest.json",
            {
                "schema_version": corpus.schema_version,
                "document_count": len(corpus.documents),
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            },
        )

        return corpus

    async def parse_trials(
        self,
        project_id: str,
        llm_provider: str = "gpt-4o-mini",
        prompt_template: str = "trialist-ner-prompt.txt",
        impl: str | None = None,
    ) -> models.TrialSchema:
        """Execute trial parsing stage."""
        ctx = self._create_context(project_id)
        config = load_config(self.config_path)
        impl_name = self._get_impl_name("parse-trials", impl, config)

        # Get implementation from registry
        parser = registry.get_parser(impl_name)

        # Load corpus from disk
        # load_corpus_from_disk is now imported at the top

        corpus = load_corpus_from_disk(ctx)

        # Create params using CLI models
        params = models.ParseTrialsParams(
            llm_provider=llm_provider,
            prompt_template=prompt_template,
            validation_resources=None,
        )

        # Execute
        schema = parser.run(params, ctx, corpus)

        # Save to workspace
        out_dir = stage_path(ctx, "schema")
        write_json(out_dir / "trial_schema.json", dataclass_to_dict(schema))

        return schema

    async def map_to_ehr(
        self,
        project_id: str,
        ehr_source: str = "mimic",
        dictionary: str | None = None,
        output_format: str = "json",
        impl: str | None = None,
    ) -> models.FilterSpec:
        """Execute EHR mapping stage."""
        ctx = self._create_context(project_id)
        config = load_config(self.config_path)
        impl_name = self._get_impl_name("map-to-ehr", impl, config)

        # Get implementation from registry
        mapper = registry.get_mapper(impl_name)

        # Load schema from disk
        # load_schema_from_disk is now imported at the top

        schema = load_schema_from_disk(ctx)

        # Load variable dictionary
        variable_dict = load_variable_dictionary(
            Path(dictionary) if dictionary else None
        )

        # Create params using CLI models
        params = models.MapToEHRParams(
            ehr_source=ehr_source,
            variable_dictionary=variable_dict,
            output_format=output_format,
        )

        # Execute
        spec = mapper.run(params, ctx, schema)

        # Save to workspace
        out_dir = stage_path(ctx, "filters")
        write_json(out_dir / "filter_spec.json", dataclass_to_dict(spec))
        if output_format == "sql":
            import json

            sql_lines = [
                "-- Synthetic SQL generated from filter spec",
                "SELECT * FROM cohort_source WHERE",
            ]
            for expr in spec.inclusion_filters:
                condition = expr.expr
                sql_lines.append(
                    f"  {condition['field']} {condition['op']} {json.dumps(condition['value'])}"
                )
            write_text(out_dir / "filter_spec.sql", "\n".join(sql_lines))

        return spec

    async def filter_cohort(
        self,
        project_id: str,
        input_uri: str = "duckdb:///synthetic.duckdb",
        sample_size: int | None = None,
        dry_run: bool = False,
        impl: str | None = None,
    ) -> models.CohortResult:
        """Execute cohort filtering stage."""
        ctx = self._create_context(project_id)
        config = load_config(self.config_path)
        impl_name = self._get_impl_name("filter-cohort", impl, config)

        # Get implementation from registry
        extractor = registry.get_cohort(impl_name)

        # Load filter spec from disk
        # load_filter_spec_from_disk is now imported at the top

        spec = load_filter_spec_from_disk(ctx)

        # Create params using CLI models
        params = models.FilterCohortParams(
            input_uri=input_uri,
            sample_size=sample_size,
            dry_run=dry_run,
            parallelism=1,
        )

        # Execute
        cohort = extractor.run(params, ctx, spec)

        # Save to workspace
        out_dir = stage_path(ctx, "cohort")
        rows_list = [dataclass_to_dict(row) for row in cohort.rows]
        write_parquet(out_dir / "cohort.parquet", rows_list)
        write_json(
            out_dir / "cohort.json",
            {
                "schema_version": cohort.schema_version,
                "rows": [
                    {
                        **{k: v for k, v in row.items() if k != "index_time"},
                        "index_time": row["index_time"].isoformat(),
                    }
                    for row in rows_list
                ],
                "summary": cohort.summary,
            },
        )
        write_json(out_dir / "summary.json", cohort.summary)

        return cohort

    async def filter_cohort_demo(
        self,
        project_id: str,
        nct_id: str,
        sample_size: int | None = None,
        dry_run: bool = False,
    ) -> models.CohortResult:
        """
        Execute cohort filtering using pre-prepared SQL (demo mode).

        This method bypasses the normal map-to-ehr → filter-cohort workflow
        by using pre-written SQL queries from fixtures.

        Args:
            project_id: Project identifier
            nct_id: NCT ID (for fixture lookup)
            sample_size: Optional sample size limit
            dry_run: If True, don't execute SQL

        Returns:
            CohortResult with extracted cohort
        """
        if not self.demo_loader:
            raise ValueError("Demo loader not initialized. Set DEMO_MODE=true in .env")

        ctx = self._create_context(project_id)

        # Normalize NCT ID
        nct_normalized = nct_id.upper()
        if not nct_normalized.startswith("NCT"):
            nct_normalized = f"NCT{nct_id.upper().replace('NCT', '')}"

        self.logger.info(f"🎯 Demo mode: Loading pre-built SQL for {nct_normalized}")

        # Load pre-built SQL
        sql = self.demo_loader.load_prebuilt_sql(nct_normalized)

        # Load pre-built schema (for metadata)
        schema = self.demo_loader.load_prebuilt_schema(nct_normalized, ctx)

        # Create FilterSpec with SQL embedded
        filter_spec = self.demo_loader.sql_to_filter_spec(sql, nct_normalized, schema)

        # Create params
        params = models.FilterCohortParams(
            input_uri="duckdb://mimic",  # Placeholder
            sample_size=sample_size,
            dry_run=dry_run,
            parallelism=1,
        )

        # Execute SQL using MimicDemoCohortExtractor
        extractor = MimicDemoCohortExtractor()
        cohort = extractor.run_sql_direct(sql, params, ctx, filter_spec)

        # Save to workspace
        out_dir = stage_path(ctx, "cohort")
        rows_list = [dataclass_to_dict(row) for row in cohort.rows]
        write_parquet(out_dir / "cohort.parquet", rows_list)
        write_json(
            out_dir / "cohort.json",
            {
                "schema_version": cohort.schema_version,
                "rows": [
                    {
                        **{k: v for k, v in row.items() if k != "index_time"},
                        "index_time": row["index_time"].isoformat(),
                    }
                    for row in rows_list
                ],
                "summary": cohort.summary,
            },
        )
        write_json(out_dir / "summary.json", cohort.summary)

        self.logger.info(f"✅ Demo cohort extracted: {cohort.summary.get('total_subjects', 0)} subjects")

        return cohort

    async def analyze_outcomes(
        self,
        project_id: str,
        treatment_column: str = "on_arnI",
        outcome_column: str = "mortality_30d",
        estimators: list[str] = None,
        impl: str | None = None,
    ) -> models.AnalysisMetrics:
        """Execute outcome analysis stage."""
        ctx = self._create_context(project_id)
        config = load_config(self.config_path)
        impl_name = self._get_impl_name("analyze", impl, config)

        # Get implementation from registry
        analyzer = registry.get_analyzer(impl_name)

        # Load cohort from disk
        # load_cohort_from_disk is now imported at the top

        cohort = load_cohort_from_disk(ctx)

        # Create params using CLI models
        params = models.AnalyzeParams(
            treatment_column=treatment_column,
            outcome_column=outcome_column,
            estimators=estimators or ["synthetic"],
            feature_config=None,
            log_to=None,
        )

        # Execute
        analysis = analyzer.run(params, ctx, cohort)

        # Save to workspace
        out_dir = stage_path(ctx, "analysis")
        outcomes_list = [dataclass_to_dict(row) for row in analysis.outcomes]
        write_parquet(out_dir / "outcomes.parquet", outcomes_list)
        write_json(
            out_dir / "outcomes.json",
            {
                "schema_version": analysis.schema_version,
                "outcomes": [
                    {
                        **{
                            k: v
                            for k, v in row.items()
                            if k not in {"propensity", "ate", "predicted_outcome"}
                        },
                        "propensity": row.get("propensity"),
                        "ate": row.get("ate"),
                        "predicted_outcome": row.get("predicted_outcome"),
                    }
                    for row in outcomes_list
                ],
            },
        )
        write_json(out_dir / "metrics.json", analysis.metrics)

        return analysis

    async def write_report(
        self,
        project_id: str,
        template: str,
        format: str = "markdown",
        hil_review: bool = False,
        impl: str | None = None,
    ) -> models.ReportBundle:
        """Execute report generation stage."""
        ctx = self._create_context(project_id)
        config = load_config(self.config_path)
        impl_name = self._get_impl_name("write-report", impl, config)

        # Get implementation from registry
        generator = registry.get_report(impl_name)

        # Load analysis from disk
        # load_analysis_from_disk is now imported at the top

        analysis = load_analysis_from_disk(ctx)

        # Create params using CLI models
        params = models.WriteReportParams(
            template_path=Path(template),
            output_format=format,
            hil_review=hil_review,
        )

        # Execute
        bundle = generator.run(params, ctx, analysis)

        # Save to workspace
        out_dir = stage_path(ctx, "report")
        write_text(out_dir / "report.md", bundle.report_body)
        figures_dir = out_dir / "figures"
        for figure in bundle.figures:
            ext = "png" if figure.media_type == "image/png" else "bin"
            write_binary(figures_dir / f"{figure.name}.{ext}", figure.data)
        if format == "pdf":
            write_text(
                out_dir / "report.pdf.txt",
                "PDF generation is not implemented in synthetic mode.",
            )

        return bundle

    async def run_stimula(
        self,
        project_id: str,
        vary: list[str] | None = None,
        max_variations: int = 3,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute what-if simulation."""
        # load_cohort_from_disk is now imported at the top, parse_variations

        ctx = self._create_context(project_id)

        # Load cohort
        cohort = load_cohort_from_disk(ctx)
        rows = list(cohort.rows)
        baseline_total = len(rows)

        # Define feature registry
        def lt(a, b):
            try:
                return a is not None and float(a) < float(b)
            except Exception:
                return False

        def gt(a, b):
            try:
                return a is not None and float(a) > float(b)
            except Exception:
                return False

        registry_map = {
            "LVEF_LT": ("lvef", lt),
            "BNP_GT": ("bnp", gt),
            "AGE_MIN": ("age", gt),
            "AGE_MAX": ("age", lt),
        }

        scenarios = []
        variations = parse_variations(vary, max_variations)
        seen_keys = set()

        for key, threshold in variations:
            feature_key, comp = registry_map.get(key, (None, None))
            if feature_key is None:
                scenarios.append(
                    {
                        "variation": f"{key}={threshold}",
                        "note": "unsupported variation key (display-only)",
                    }
                )
                continue

            kept = [
                r
                for r in rows
                if comp((r.features or {}).get(feature_key), threshold)
            ]
            scenarios.append(
                {
                    "variation": f"{key}={threshold}",
                    "applied_on": feature_key,
                    "threshold": threshold,
                    "kept_subjects": len(kept),
                    "dropped_subjects": baseline_total - len(kept),
                    "keep_rate": (len(kept) / baseline_total) if baseline_total else 0.0,
                    "sample_subjects": [str(getattr(r, "subject_id")) for r in kept[:5]],
                }
            )
            seen_keys.add(key)

        # Save to workspace
        out_dir = stage_path(ctx, "stimula")
        write_json(
            out_dir / "plan.json",
            {"max_variations": max_variations, "keys": list(seen_keys)},
        )
        write_jsonl(out_dir / "sweep_results.jsonl", scenarios)
        write_json(
            out_dir / "manifest.json",
            {
                "schema_version": "stimula.v1",
                "scenario_count": len(scenarios),
                "baseline_subjects": baseline_total,
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            },
        )

        return {
            "scenario_count": len(scenarios),
            "baseline_subjects": baseline_total,
            "scenarios": scenarios,
        }

    async def run_all(
        self,
        project_id: str,
        disease_code: str,
        keywords: list[str],
        sources: list[str],
        estimators: list[str],
        template: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Execute full pipeline."""
        # Search literature
        corpus = await self.search_literature(
            project_id=project_id,
            disease_code=disease_code,
            keywords=keywords,
            sources=sources,
            max_records=kwargs.get("max_records", 5),
            require_full_text=kwargs.get("require_full_text", False),
        )

        # Parse trials
        schema = await self.parse_trials(
            project_id=project_id,
            llm_provider=kwargs.get("llm_provider", "synthetic-llm"),
            prompt_template=kwargs.get("prompt_template", "default-trial-prompt.txt"),
        )

        # Map to EHR
        spec = await self.map_to_ehr(
            project_id=project_id,
            ehr_source=kwargs.get("ehr_source", "mimic"),
            dictionary=kwargs.get("dictionary"),
            output_format=kwargs.get("filters_format", "json"),
        )

        # Filter cohort
        cohort = await self.filter_cohort(
            project_id=project_id,
            input_uri=kwargs.get("input_uri", "duckdb:///synthetic.duckdb"),
            sample_size=kwargs.get("sample_size"),
            dry_run=False,
        )

        # Analyze outcomes
        analysis = await self.analyze_outcomes(
            project_id=project_id,
            treatment_column=kwargs.get("treatment_column", "on_arnI"),
            outcome_column=kwargs.get("outcome_column", "mortality_30d"),
            estimators=estimators,
        )

        # Write report
        bundle = await self.write_report(
            project_id=project_id,
            template=template,
            format=kwargs.get("report_format", "markdown"),
            hil_review=False,
        )

        return {
            "literature": {
                "document_count": len(corpus.documents),
                "schema_version": corpus.schema_version,
            },
            "parsing": {
                "disease_code": schema.disease_code,
                "inclusion_count": len(schema.inclusion),
                "exclusion_count": len(schema.exclusion),
                "feature_count": len(schema.features),
            },
            "mapping": {
                "ehr_source": spec.ehr_source,
                "variable_map_count": len(spec.variable_map),
                "inclusion_filters_count": len(spec.inclusion_filters),
                "exclusion_filters_count": len(spec.exclusion_filters),
            },
            "cohort": {
                "total_subjects": cohort.summary.get("total_subjects", 0),
                "summary": cohort.summary,
            },
            "analysis": {
                "outcome_count": len(list(analysis.outcomes)),
                "metrics_summary": analysis.metrics.get("summary", {}),
            },
            "report": {
                "report_body_length": len(bundle.report_body),
                "figure_count": len(bundle.figures),
            },
        }

