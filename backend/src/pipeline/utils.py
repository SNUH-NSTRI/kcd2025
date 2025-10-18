"""Utility functions for pipeline execution."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping

from . import models
from .context import PipelineContext

STAGE_ALIAS = {
    "search-lit": "search",
    "parse-trials": "parser",
    "map-to-ehr": "mapper",
    "filter-cohort": "filter",
    "analyze": "analyzer",
    "write-report": "report",
}

DEFAULT_VARIABLE_DICTIONARY: Mapping[str, Any] = {
    "tables": {
        "echodata": {
            "columns": {
                "lvef": {"unit": "percent"},
                "study_time": {"description": "Echo study timestamp"},
            }
        },
        "labevents": {
            "columns": {
                "bnp": {"unit": "pg/mL"},
                "valuenum": {"unit": "generic"},
            }
        },
        "patients": {
            "columns": {
                "age": {"unit": "year"},
                "subject_id": {"description": "patient key"},
            }
        },
        "prescriptions": {
            "columns": {
                "drug": {"description": "drug name"},
                "starttime": {"description": "start timestamp"},
            }
        },
    },
    "mappings": {
        "BNP": {"concept_id": 50822, "preferred_unit": "pg/mL"},
        "LVEF": {"concept_id": 51000, "preferred_unit": "percent"},
    },
}


def resolve_impl_name(
    stage: str, config: Mapping[str, Any], overrides: Mapping[str, str]
) -> str:
    """Resolve implementation name for a pipeline stage."""
    if stage in overrides:
        return overrides[stage]
    alias = STAGE_ALIAS.get(stage, stage)
    default_impls = (
        config.get("project", {}).get("default_impls", {}) if config else {}
    )

    # Define stage-specific defaults (NO synthetic data generation)
    stage_defaults = {
        "search": "langgraph-search",  # ALWAYS use real ClinicalTrials.gov API
        "parser": "trialist",
        "mapper": "mimic-demo",
        "filter": "mimic-demo",
        "analyzer": "synthetic",
        "report": "synthetic",
    }

    return default_impls.get(alias, stage_defaults.get(alias, "synthetic"))


def stage_path(ctx: PipelineContext, stage: str) -> Path:
    """Get workspace path for a pipeline stage."""
    return ctx.workspace / ctx.project_id / stage


def load_corpus_from_disk(ctx: PipelineContext) -> models.LiteratureCorpus:
    """Load literature corpus from workspace.

    Reads corpus.json (our standard format) which contains:
    {
        "schema_version": "lit.v1",
        "documents": [...],
        "document_count": N,
        "generated_at": "ISO timestamp"
    }
    """
    corpus_file = stage_path(ctx, "lit") / "corpus.json"
    if not corpus_file.exists():
        raise FileNotFoundError("literature corpus not found in workspace")

    with corpus_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    documents: list[models.LiteratureDocument] = []
    for payload in data.get("documents", []):
        fetched_at = dt.datetime.fromisoformat(payload["fetched_at"])
        documents.append(
            models.LiteratureDocument(
                source=payload["source"],
                identifier=payload["identifier"],
                title=payload["title"],
                abstract=payload.get("abstract"),
                full_text=payload.get("full_text"),
                fetched_at=fetched_at,
                url=payload.get("url"),
                metadata=payload.get("metadata"),
            )
        )

    return models.LiteratureCorpus(
        schema_version=data.get("schema_version", "lit.v1"),
        documents=documents
    )


def load_schema_from_disk(ctx: PipelineContext) -> models.TrialSchema:
    """Load trial schema from workspace."""
    schema_file = stage_path(ctx, "schema") / "trial_schema.json"
    if not schema_file.exists():
        raise FileNotFoundError("trial schema not found in workspace")
    payload = json.loads(schema_file.read_text(encoding="utf-8"))
    inclusion = [
        models.TrialCriterion(
            id=item["id"],
            description=item["description"],
            category=item["category"],
            kind=item["kind"],
            value=item["value"],
        )
        for item in payload["inclusion"]
    ]
    exclusion = [
        models.TrialCriterion(
            id=item["id"],
            description=item["description"],
            category=item["category"],
            kind=item["kind"],
            value=item["value"],
        )
        for item in payload["exclusion"]
    ]
    features = [
        models.TrialFeature(
            name=item["name"],
            source=item["source"],
            unit=item.get("unit"),
            time_window=tuple(item["time_window"]) if item.get("time_window") else None,
            metadata=item.get("metadata"),
        )
        for item in payload["features"]
    ]
    return models.TrialSchema(
        schema_version=payload["schema_version"],
        disease_code=payload["disease_code"],
        inclusion=inclusion,
        exclusion=exclusion,
        features=features,
        provenance=payload.get("provenance", {}),
    )


def load_filter_spec_from_disk(ctx: PipelineContext) -> models.FilterSpec:
    """Load filter specification from workspace."""
    spec_file = stage_path(ctx, "filters") / "filter_spec.json"
    if not spec_file.exists():
        raise FileNotFoundError("filter spec not found in workspace")
    payload = json.loads(spec_file.read_text(encoding="utf-8"))
    variable_map = [
        models.VariableMapping(
            schema_feature=item["schema_feature"],
            ehr_table=item["ehr_table"],
            column=item["column"],
            concept_id=item.get("concept_id"),
            transform=item.get("transform"),
        )
        for item in payload["variable_map"]
    ]
    inclusion_filters = [
        models.FilterExpression(
            criterion_id=item["criterion_id"],
            expr=item["expr"],
        )
        for item in payload["inclusion_filters"]
    ]
    exclusion_filters = [
        models.FilterExpression(
            criterion_id=item["criterion_id"],
            expr=item["expr"],
        )
        for item in payload["exclusion_filters"]
    ]
    return models.FilterSpec(
        schema_version=payload["schema_version"],
        ehr_source=payload["ehr_source"],
        variable_map=variable_map,
        inclusion_filters=inclusion_filters,
        exclusion_filters=exclusion_filters,
        lineage=payload.get("lineage", {}),
    )


def load_cohort_from_disk(ctx: PipelineContext) -> models.CohortResult:
    """Load cohort result from workspace."""
    cohort_file = stage_path(ctx, "cohort") / "cohort.json"
    if not cohort_file.exists():
        raise FileNotFoundError("cohort dataset not found in workspace")
    payload = json.loads(cohort_file.read_text(encoding="utf-8"))
    rows = [
        models.CohortRow(
            subject_id=item["subject_id"],
            stay_id=item.get("stay_id"),
            matched_criteria=item.get("matched_criteria", []),
            index_time=dt.datetime.fromisoformat(item["index_time"]),
            features=item.get("features"),
        )
        for item in payload["rows"]
    ]
    return models.CohortResult(
        schema_version=payload["schema_version"],
        rows=rows,
        summary=payload["summary"],
    )


def load_analysis_from_disk(ctx: PipelineContext) -> models.AnalysisMetrics:
    """Load analysis metrics from workspace."""
    analysis_dir = stage_path(ctx, "analysis")
    outcomes_file = analysis_dir / "outcomes.json"
    metrics_file = analysis_dir / "metrics.json"
    if not outcomes_file.exists() or not metrics_file.exists():
        raise FileNotFoundError("analysis artifacts not found in workspace")
    outcomes_payload = json.loads(outcomes_file.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    outcomes = [
        models.OutcomeRecord(
            subject_id=item["subject_id"],
            propensity=item.get("propensity"),
            ate=item.get("ate"),
            cate_group=item.get("cate_group"),
            predicted_outcome=item.get("predicted_outcome"),
            metadata=item.get("metadata"),
        )
        for item in outcomes_payload["outcomes"]
    ]
    return models.AnalysisMetrics(
        schema_version=outcomes_payload["schema_version"],
        outcomes=outcomes,
        metrics=metrics,
    )


def parse_variations(value: str) -> dict[str, list[Any]]:
    """Parse stimula variation specification."""
    try:
        result = json.loads(value)
        if not isinstance(result, dict):
            raise ValueError("Variations must be a JSON object")
        for key, vals in result.items():
            if not isinstance(vals, list):
                raise ValueError(f"Variation '{key}' must be a list of values")
        return result
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in --vary: {exc}") from exc


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load configuration from file."""
    if config_path is None:
        return {}
    
    # Convert string to Path
    if isinstance(config_path, str):
        config_path = Path(config_path)
        
    if not config_path.exists():
        return {}
        
    try:
        config_text = config_path.read_text(encoding="utf-8")
        
        # Try YAML first, then JSON
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            try:
                import yaml
                return yaml.safe_load(config_text) or {}
            except ImportError:
                # Fallback to basic YAML parsing if pyyaml not available
                return _parse_simple_yaml(config_text)
        else:
            return json.loads(config_text)
    except Exception:
        return {}


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Simple YAML parser for basic configurations (fallback)."""
    config = {}
    current_section = config
    section_stack = []
    
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # Count indentation
        indent = len(line) - len(line.lstrip())
        line = line.lstrip()
        
        if ':' in line and not line.startswith('-'):
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            if not value:  # Section header
                new_section = {}
                current_section[key] = new_section
                section_stack = [(current_section, key)]
                current_section = new_section
            else:
                # Parse basic values
                if value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                    
                current_section[key] = value
                
    return config


def load_variable_dictionary(path: Path | None) -> Mapping[str, Any]:
    """Load variable dictionary from file or return default."""
    if path is None:
        return DEFAULT_VARIABLE_DICTIONARY
    if not path.exists():
        raise FileNotFoundError(f"Variable dictionary not found at {path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_VARIABLE_DICTIONARY)
        if "tables" in loaded:
            if "tables" not in merged:
                merged["tables"] = {}
            for table_name, table_def in loaded["tables"].items():
                if table_name not in merged["tables"]:
                    merged["tables"][table_name] = table_def
                else:
                    merged_table = dict(merged["tables"][table_name])
                    if "columns" in table_def:
                        if "columns" not in merged_table:
                            merged_table["columns"] = {}
                        merged_table["columns"].update(table_def["columns"])
                    merged["tables"][table_name] = merged_table
        if "mappings" in loaded:
            if "mappings" not in merged:
                merged["mappings"] = {}
            merged["mappings"].update(loaded["mappings"])
        return merged
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in variable dictionary: {exc}") from exc


__all__ = [
    "STAGE_ALIAS",
    "DEFAULT_VARIABLE_DICTIONARY",
    "resolve_impl_name",
    "stage_path",
    "load_corpus_from_disk",
    "load_schema_from_disk",
    "load_filter_spec_from_disk",
    "load_cohort_from_disk",
    "load_analysis_from_disk",
    "parse_variations",
    "load_config",
    "load_variable_dictionary",
]

