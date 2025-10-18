"""
Pydantic schemas for Eligibility Extraction with Human-in-the-Loop Learning System.

This module defines the core data models for extracting and managing clinical trial
eligibility criteria. These schemas are used throughout the system:
- LLM extraction output
- API request/response contracts
- Frontend form data structures
- Correction storage and retrieval
"""

from datetime import datetime
from typing import Any, List, Literal, Union

from pydantic import BaseModel, Field


class EligibilityCriterion(BaseModel):
    """
    Individual eligibility criterion with structured fields.

    This represents a single inclusion or exclusion criterion extracted from
    a clinical trial's eligibility section.
    """

    id: str = Field(..., description="Unique ID within extraction: 'inc_1', 'exc_1'")
    type: Literal["inclusion", "exclusion"] = Field(..., description="Criterion type")
    key: str = Field(
        ...,
        description="Main concept: 'Age', 'ECOG Performance Status', 'Hemoglobin'",
    )
    operator: Literal[">=", "<=", "==", "!=", "in", "not_in", "between", "contains"] = Field(
        ..., description="Comparison operator"
    )
    value: Any = Field(
        ...,
        description="Threshold/target value. For 'between': [min, max]. For 'in': [value1, value2, ...]",
    )
    unit: str | None = Field(default=None, description="Unit: 'years', 'g/dL', 'mg/mL'")
    original_text: str = Field(..., description="Original NCT text snippet for reference")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "inc_1",
                    "type": "inclusion",
                    "key": "Age",
                    "operator": ">=",
                    "value": 18,
                    "unit": "years",
                    "original_text": "Age 18 years or older",
                },
                {
                    "id": "exc_2",
                    "type": "exclusion",
                    "key": "Pregnancy",
                    "operator": "==",
                    "value": "positive",
                    "unit": None,
                    "original_text": "Pregnant or breastfeeding women",
                },
            ]
        }


class EligibilityExtraction(BaseModel):
    """
    Complete eligibility extraction result from LLM or human correction.

    This is the central data structure that flows through the entire system:
    - LLM extracts criteria into this format
    - Frontend displays and edits this structure
    - Corrections compare original vs. corrected versions of this
    """

    inclusion: List[EligibilityCriterion] = Field(
        default_factory=list, description="List of inclusion criteria"
    )
    exclusion: List[EligibilityCriterion] = Field(
        default_factory=list, description="List of exclusion criteria"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Model's confidence in the extraction (0.0-1.0)"
    )
    model_version: str = Field(
        default="gpt-4o-mini-2024-07-18", description="Model version used for extraction"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp of extraction"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "inclusion": [
                    {
                        "id": "inc_1",
                        "type": "inclusion",
                        "key": "Age",
                        "operator": ">=",
                        "value": 18,
                        "unit": "years",
                        "original_text": "Age 18 years or older",
                    }
                ],
                "exclusion": [],
                "confidence_score": 0.92,
                "model_version": "gpt-4o-mini-2024-07-18",
                "extracted_at": "2025-10-17T14:30:00Z",
            }
        }


class CorrectionMetadata(BaseModel):
    """
    Metadata about the clinical trial study for correction indexing.

    Used by CorrectionManager to select relevant examples based on:
    - Condition similarity
    - Keyword overlap
    - Phase matching
    """

    nct_id: str = Field(..., pattern=r"^NCT\d{8}$", description="NCT trial identifier")
    condition: str = Field(
        ..., description="Normalized condition: 'sepsis', 'diabetes', 'cancer'"
    )
    phase: str | None = Field(
        default=None, description="Trial phase: 'phase_1', 'phase_2', 'phase_3'"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="User-tagged keywords: 'age_criteria', 'pregnancy_exclusion'",
    )


class QualityMetrics(BaseModel):
    """
    Metrics assessing the quality of a correction.

    Quality score determines whether a correction is used as an example
    for future extractions. Lower quality corrections (< 0.7) are excluded.
    """

    quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall quality score (0.0-1.0)"
    )
    num_changes: int = Field(..., ge=0, description="Number of changes made by user")


class CorrectionExtractionPayload(BaseModel):
    """
    Container for original AI output and human-corrected version.

    This preserves both versions for:
    - Audit trail
    - Quality assessment
    - Training data generation
    """

    original_ai_output: EligibilityExtraction = Field(
        ..., description="Original extraction from LLM"
    )
    human_corrected: EligibilityExtraction = Field(
        ..., description="Corrected version after human review"
    )
    changes: List[dict] = Field(
        default_factory=list,
        description="List of changes made: [{'field': 'inclusion[0].value', 'old': 16, 'new': 18}]",
    )


class Correction(BaseModel):
    """
    Complete correction record stored in workspace/corrections/data/{nct_id}/{timestamp}.json

    This is the primary unit of learning in the HITL system. Each correction becomes
    a potential example for future extractions.
    """

    nct_id: str = Field(..., pattern=r"^NCT\d{8}$", description="NCT trial identifier")
    corrected_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp of correction"
    )
    corrected_by: str = Field(default="anonymous", description="User who made the correction")
    study_metadata: CorrectionMetadata = Field(
        ..., description="Metadata for example selection"
    )
    extraction: CorrectionExtractionPayload = Field(
        ..., description="Original and corrected extractions"
    )
    quality_metrics: QualityMetrics = Field(..., description="Quality assessment")

    class Config:
        json_schema_extra = {
            "example": {
                "nct_id": "NCT03389555",
                "corrected_at": "2025-10-17T14:30:00Z",
                "corrected_by": "user@example.com",
                "study_metadata": {
                    "nct_id": "NCT03389555",
                    "condition": "sepsis",
                    "phase": "phase_3",
                    "keywords": ["age_criteria", "organ_dysfunction"],
                },
                "extraction": {
                    "original_ai_output": {"inclusion": [], "exclusion": []},
                    "human_corrected": {"inclusion": [], "exclusion": []},
                    "changes": [],
                },
                "quality_metrics": {"quality_score": 0.95, "num_changes": 2},
            }
        }


# ============================================================================
# API Request/Response Models
# ============================================================================


class ExtractRequest(BaseModel):
    """Request to extract eligibility criteria from NCT data."""

    nct_id: str = Field(..., pattern=r"^NCT\d{8}$", description="NCT trial identifier")


class ExtractResponse(BaseModel):
    """Response containing extracted eligibility criteria."""

    nct_id: str
    extraction: EligibilityExtraction
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall extraction confidence")
    examples_used: List[str] = Field(
        default_factory=list, description="NCT IDs of examples used for extraction"
    )
    selection_strategy: str = Field(
        default="hybrid",
        description="Strategy used: 'condition_match', 'keyword_overlap', 'recent', 'hybrid', 'cold_start'",
    )


class ReviewRequest(BaseModel):
    """Request to submit a review/correction of an extraction."""

    nct_id: str = Field(..., pattern=r"^NCT\d{8}$")
    action: Literal["accept", "edit"] = Field(
        ..., description="'accept' for as-is, 'edit' for corrections"
    )
    original_extraction: EligibilityExtraction = Field(..., description="Original AI output")
    corrected_extraction: EligibilityExtraction | None = Field(
        default=None, description="Required if action='edit'"
    )
    keywords: List[str] = Field(
        default_factory=list, description="User-selected keywords for indexing"
    )


class ReviewResponse(BaseModel):
    """Response after submitting a review."""

    status: Literal["accepted", "saved"]
    message: str
    correction_id: str | None = Field(
        default=None, description="Correction file path if action='edit'"
    )


class CorrectionStatsResponse(BaseModel):
    """Statistics about the correction system."""

    total_corrections: int
    by_condition: dict[str, int] = Field(default_factory=dict)
    by_keyword: dict[str, int] = Field(default_factory=dict)
    average_quality_score: float
    recent_corrections: List[str] = Field(
        default_factory=list, description="NCT IDs of recent corrections"
    )
