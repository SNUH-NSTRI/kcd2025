"""
Enhanced models for Trialist Agent implementation.

This module extends the base pipeline models with enhanced NER capabilities,
standardization features, and CDM mapping support.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, Protocol, Literal

from .context import PipelineContext
from . import models


# Enhanced entity types with domain classification
@dataclass(frozen=True)
class EnhancedNamedEntity:
    """Enhanced named entity with domain classification and standardization."""
    text: str
    type: Literal["concept", "temporal", "value"]
    domain: str  # Domain classification (Demographic, Condition, Drug, etc.)
    start: int | None = None
    end: int | None = None
    confidence: float | None = None

    # Standardization fields (Stage 2)
    standard_name: str | None = None
    umls_cui: str | None = None

    # CDM mapping fields (Stage 3)
    code_system: str | None = None
    code_set: Sequence[str] | None = None
    primary_code: str | None = None

    # Value extraction fields (Phase 1.1)
    operator: str | None = None  # <, >, ≥, ≤, =, between
    numeric_value: float | None = None  # Single numeric value
    value_range: tuple[float, float] | None = None  # Range for "between" operator
    unit: str | None = None  # Original unit string
    ucum_unit: str | None = None  # UCUM-standardized unit

    # Temporal normalization fields (Phase 1.3)
    temporal_pattern: str | None = None  # Temporal pattern type (XWithinTime, XBeforeY, etc.)
    iso_duration: str | None = None  # ISO 8601 duration (P3M, PT24H, P1Y)
    reference_point: str | None = None  # Reference concept (enrollment, admission, baseline)

    # Relationship fields (Phase 2.1)
    logical_operator: str | None = None  # AND, OR for compound concepts
    related_entity_ids: Sequence[str] | None = None  # IDs of related entities in compound expression

    # Inference fields (Phase 2.2)
    is_inferred: bool = False  # Whether this concept was inferred
    inferred_from: str | None = None  # Source text that triggered inference

    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class TemporalRelation:
    """Temporal relationship between concepts."""
    pattern: str  # e.g., "XBeforeYwithTime", "XWithinTime"
    value: str  # e.g., "3 months", "24 hours"
    normalized_duration: str | None = None  # ISO 8601 format (P3M, PT24H)
    subject_concept: str | None = None  # Text of subject concept
    reference_concept: str | None = None  # Text of reference concept
    confidence: float | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ProcessingStageInfo:
    """Information about each processing stage."""
    stage_name: str
    execution_time_ms: float
    success: bool
    error_message: str | None = None
    entities_processed: int | None = None
    concepts_standardized: int | None = None
    codes_mapped: int | None = None


@dataclass(frozen=True)
class EnhancedTrialCriterion:
    """Enhanced trial criterion with Trialist processing."""
    id: str
    description: str
    category: str
    kind: str
    value: Mapping[str, Any]
    entities: Sequence[EnhancedNamedEntity] | None = None
    
    # Processing metadata
    processing_stages: Sequence[ProcessingStageInfo] | None = None
    validation_score: float | None = None


@dataclass(frozen=True)
class EnhancedTrialFeature:
    """Enhanced trial feature with Trialist processing."""
    name: str
    source: str
    unit: str | None
    time_window: tuple[int, int] | None
    metadata: Mapping[str, Any] | None = None
    entities: Sequence[EnhancedNamedEntity] | None = None
    
    # Processing metadata
    processing_stages: Sequence[ProcessingStageInfo] | None = None
    validation_score: float | None = None


@dataclass(frozen=True)
class EnhancedTrialSchema:
    """Enhanced trial schema with Trialist processing."""
    schema_version: str
    disease_code: str
    inclusion: Sequence[EnhancedTrialCriterion]
    exclusion: Sequence[EnhancedTrialCriterion]
    features: Sequence[EnhancedTrialFeature] | None = None
    provenance: Mapping[str, Any] | None = None

    # Trialist enhancements
    outcomes: Sequence[EnhancedNamedEntity] | None = None  # Primary/Secondary outcomes
    temporal_relations: Sequence[TemporalRelation] | None = None
    domain_statistics: Mapping[str, int] | None = None  # Entity count by domain
    vocabulary_coverage: Mapping[str, float] | None = None  # Coverage by code system


# Configuration models
@dataclass(frozen=True)
class TrialistNERParams:
    """Parameters for NER stage."""
    max_granularity: bool = True
    inference_enabled: bool = True
    confidence_threshold: float = 0.7
    domain_taxonomy: Sequence[str] | None = None


@dataclass(frozen=True)
class TrialistStandardizationParams:
    """Parameters for standardization stage."""
    umls_api_key: str | None = None
    ohdsi_endpoint: str = "https://athena.ohdsi.org/api"
    temporal_ontology: str = "time_event_v1"
    confidence_threshold: float = 0.8


@dataclass(frozen=True)
class TrialistCDMParams:
    """Parameters for CDM mapping stage."""
    primary_vocabularies: Mapping[str, str] | None = None
    fallback_enabled: bool = True
    validation_enabled: bool = True
    confidence_threshold: float = 0.75


@dataclass(frozen=True)
class TrialistParams:
    """Complete parameters for Trialist processing."""
    llm_provider: str = "gpt-4o-mini"
    temperature: float = 0.0
    
    ner_params: TrialistNERParams | None = None
    standardization_params: TrialistStandardizationParams | None = None
    cdm_params: TrialistCDMParams | None = None
    
    # Legacy compatibility
    prompt_template: str = "trialist-ner-prompt.txt"
    validation_resources: Mapping[str, Any] | None = None


# Protocol definitions
class TrialistProcessor(Protocol):
    """Protocol for Trialist processing implementations."""
    
    def run(
        self,
        params: TrialistParams,
        ctx: PipelineContext,
        corpus: models.LiteratureCorpus,
    ) -> EnhancedTrialSchema: ...


class NERStage(Protocol):
    """Protocol for NER stage implementations."""
    
    def process(
        self,
        text: str,
        params: TrialistNERParams,
        ctx: PipelineContext,
    ) -> Sequence[EnhancedNamedEntity]: ...


class StandardizationStage(Protocol):
    """Protocol for standardization stage implementations."""
    
    def process(
        self,
        entities: Sequence[EnhancedNamedEntity],
        params: TrialistStandardizationParams,
        ctx: PipelineContext,
    ) -> tuple[Sequence[EnhancedNamedEntity], Sequence[TemporalRelation]]: ...


class CDMStage(Protocol):
    """Protocol for CDM mapping stage implementations."""
    
    def process(
        self,
        entities: Sequence[EnhancedNamedEntity],
        params: TrialistCDMParams,
        ctx: PipelineContext,
    ) -> Sequence[EnhancedNamedEntity]: ...


# Constants for domain taxonomy
DOMAIN_TAXONOMY = [
    "Demographic",
    "Condition", 
    "Device",
    "Procedure",
    "Drug",
    "Measurement",
    "Observation",
    "Visit",
    "Negation_cue",
    "Temporal",
    "Quantity",
    "Value"
]

# Default vocabulary mappings
# Note: These must match vocabulary_id values in CONCEPT.csv exactly
# IMPORTANT: Use STANDARD vocabularies (SNOMED, RxNorm, LOINC) not source vocabularies (ICD10CM)
DEFAULT_VOCABULARIES = {
    "Condition": "SNOMED",     # Standard vocabulary for Conditions (not ICD10CM)
    "Drug": "RxNorm",          # Standard vocabulary for Drugs
    "Measurement": "LOINC",    # Standard vocabulary for Measurements
    "Procedure": "SNOMED",     # Standard vocabulary for Procedures (SNOMED preferred over CPT4)
    "Device": "SNOMED",        # Standard vocabulary for Devices
    "Observation": "SNOMED",   # Standard vocabulary for Observations
    "Visit": "SNOMED"          # Standard vocabulary for Visits
}

# Temporal patterns
TEMPORAL_PATTERNS = {
    "XBeforeY": "X occurs before Y",
    "XBeforeYwithTime": "X before Y with time interval",
    "XAfterY": "X occurs after Y",
    "XAfterYwithTime": "X after Y with time interval", 
    "XDuringY": "X occurs during Y",
    "XWithinTime": "X within time period",
    "XForDuration": "X for duration",
    "XEveryInterval": "X every interval"
}


__all__ = [
    "EnhancedNamedEntity",
    "TemporalRelation",
    "ProcessingStageInfo", 
    "EnhancedTrialCriterion",
    "EnhancedTrialFeature",
    "EnhancedTrialSchema",
    "TrialistNERParams",
    "TrialistStandardizationParams",
    "TrialistCDMParams",
    "TrialistParams",
    "TrialistProcessor",
    "NERStage",
    "StandardizationStage",
    "CDMStage",
    "DOMAIN_TAXONOMY",
    "DEFAULT_VOCABULARIES",
    "TEMPORAL_PATTERNS"
]