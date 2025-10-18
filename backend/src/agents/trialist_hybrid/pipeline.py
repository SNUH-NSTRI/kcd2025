"""
Trialist Hybrid Pipeline Orchestrator.

Executes all 3 stages sequentially:
1. Stage 1: Extraction (LLM with Function Calling)
2. Stage 2: Mapping (LLM with schema validation)
3. Stage 3: Validation & SQL Generation (Deterministic, no LLM)

Error Handling:
- Strict entity-level validation (reject invalid schemas)
- Lenient trial-level aggregation (allow partial success)
"""

import time
from typing import List

from agents.trialist_hybrid.models import (
    ExtractionOutput,
    MappingOutput,
    ValidationResult,
    PipelineSummary,
    PipelineOutput,
)
from agents.trialist_hybrid.stage1_extractor import Stage1Extractor
from agents.trialist_hybrid.stage2_mapper import Stage2Mapper
from agents.trialist_hybrid.stage3_validator import Stage3Validator


class TrialistHybridPipeline:
    """
    Orchestrator for 3-stage hybrid trialist pipeline.

    Combines LLM-based extraction/mapping with deterministic validation/SQL generation.
    """

    def __init__(
        self,
        api_key: str,
        schema_path: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openai/gpt-4o",
        temperature: float = 0.0,
    ):
        """
        Initialize pipeline with all 3 stages.

        Args:
            api_key: OpenRouter API key
            schema_path: Path to MIMIC-IV schema JSON
            base_url: OpenRouter base URL
            model: LLM model name
            temperature: Sampling temperature (0.0 for deterministic)
        """
        self.stage1 = Stage1Extractor(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature
        )
        self.stage2 = Stage2Mapper(
            api_key=api_key,
            schema_path=schema_path,
            base_url=base_url,
            model=model,
            temperature=temperature
        )
        self.stage3 = Stage3Validator(schema_path=schema_path)

    def run(self, raw_criteria: str) -> PipelineOutput:
        """
        Execute full 3-stage pipeline.

        Args:
            raw_criteria: Raw trial criteria text

        Returns:
            PipelineOutput with all stage results and summary
        """
        start_time = time.time()

        extraction = self.stage1.extract(raw_criteria)

        all_criteria = extraction.inclusion + extraction.exclusion

        mappings: List[MappingOutput] = []
        for criterion in all_criteria:
            try:
                mapping = self.stage2.map_to_mimic(criterion)
                mappings.append(mapping)
            except Exception as e:
                # Lenient: Continue processing other criteria
                # Log error but don't stop pipeline
                print(f"Warning: Failed to map criterion {criterion.id}: {e}")
                continue

        validations: List[ValidationResult] = []
        for mapping in mappings:
            try:
                validation = self.stage3.validate(mapping)
                validations.append(validation)
            except Exception as e:
                # Lenient: Continue processing
                print(f"Warning: Failed to validate mapping for {mapping.criterion.id}: {e}")
                continue

        # Generate summary statistics
        execution_time = time.time() - start_time
        summary = self._generate_summary(
            extraction,
            mappings,
            validations,
            execution_time
        )

        return PipelineOutput(
            extraction=extraction,
            mappings=mappings,
            validations=validations,
            summary=summary
        )

    def _generate_summary(
        self,
        extraction: ExtractionOutput,
        mappings: List[MappingOutput],
        validations: List[ValidationResult],
        execution_time: float
    ) -> PipelineSummary:
        """
        Generate summary statistics for the pipeline run.

        Args:
            extraction: Stage 1 output
            mappings: Stage 2 outputs
            validations: Stage 3 outputs
            execution_time: Total execution time in seconds

        Returns:
            PipelineSummary with counts and rates
        """
        total_criteria = len(extraction.inclusion) + len(extraction.exclusion)

        # Stage 1 stats
        stage1_extracted = total_criteria  # All extracted criteria
        stage1_extraction_rate = 1.0 if total_criteria > 0 else 0.0

        # Stage 2 stats
        stage2_mapped = len(mappings)
        stage2_mapping_rate = stage2_mapped / total_criteria if total_criteria > 0 else 0.0

        # Stage 3 stats
        stage3_passed = sum(1 for v in validations if v.validation_status == "passed")
        stage3_warning = sum(1 for v in validations if v.validation_status == "warning")
        stage3_needs_review = sum(1 for v in validations if v.validation_status == "needs_review")
        stage3_failed = sum(1 for v in validations if v.validation_status == "failed")

        stage3_validation_rate = (
            (stage3_passed + stage3_warning) / len(validations)
            if len(validations) > 0
            else 0.0
        )

        # Average confidence
        if validations:
            avg_confidence = sum(v.confidence_score for v in validations) / len(validations)
        else:
            avg_confidence = 0.0

        return PipelineSummary(
            total_criteria=total_criteria,
            stage1_extracted=stage1_extracted,
            stage1_extraction_rate=stage1_extraction_rate,
            stage2_mapped=stage2_mapped,
            stage2_mapping_rate=stage2_mapping_rate,
            stage3_passed=stage3_passed,
            stage3_warning=stage3_warning,
            stage3_needs_review=stage3_needs_review,
            stage3_failed=stage3_failed,
            stage3_validation_rate=stage3_validation_rate,
            avg_confidence=avg_confidence,
            execution_time_seconds=round(execution_time, 2)
        )
