"""
CDM Mapper for OMOP Vocabulary Mapping

Maps UMLS CUI codes to OMOP CDM standard concepts using OHDSI WebAPI.
Implements Stage 3 of the Trialist pipeline.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .clients import OHDSIClient, OMOPConcept, CacheManager
from .trialist_models import EnhancedNamedEntity, DEFAULT_VOCABULARIES
from .time_event_mapper import TimeEventMapper

logger = logging.getLogger(__name__)


@dataclass
class CDMMapResult:
    """Result of CDM mapping operation."""

    entity: EnhancedNamedEntity
    omop_concept: Optional[OMOPConcept]
    confidence: float
    method: str  # "cui_lookup", "text_search", "fallback", "cached"
    error: Optional[str] = None


class CDMMapper:
    """
    Maps standardized medical concepts to OMOP CDM vocabularies.

    Workflow:
    1. Use UMLS CUI from Stage 2
    2. Search OHDSI for matching OMOP concept
    3. Validate standard concept status
    4. Apply domain-specific vocabulary selection
    5. Return enhanced entity with OMOP codes

    Usage:
        >>> mapper = CDMMapper(ohdsi_client, cache)
        >>> entity = EnhancedNamedEntity(text="diabetes", domain="Condition", umls_cui="C0011849")
        >>> result = mapper.map_entity(entity)
        >>> print(result.omop_concept.concept_id)  # 201826
    """

    # Confidence thresholds
    CONFIDENCE_EXACT_MATCH = 0.95
    CONFIDENCE_CUI_MATCH = 0.90
    CONFIDENCE_TEXT_SEARCH = 0.75
    CONFIDENCE_FALLBACK = 0.50

    def __init__(
        self,
        ohdsi_client: OHDSIClient,
        cache_manager: Optional[CacheManager] = None,
        fallback_enabled: bool = True,
        standard_only: bool = True,
        time_event_mapper: Optional[TimeEventMapper] = None,
        max_workers: int = 10
    ):
        """
        Initialize CDM Mapper.

        Args:
            ohdsi_client: OHDSI WebAPI client for OMOP lookups
            cache_manager: Optional cache for repeated lookups
            fallback_enabled: Enable text-based fallback if CUI mapping fails
            standard_only: Return only standard OMOP concepts
            time_event_mapper: Time Event Ontology mapper for Temporal/Value/Quantity entities
            max_workers: Maximum number of parallel workers for batch processing
        """
        self.ohdsi_client = ohdsi_client
        self.cache = cache_manager
        self.fallback_enabled = fallback_enabled
        self.standard_only = standard_only
        self.time_event_mapper = time_event_mapper or TimeEventMapper()
        self.max_workers = max_workers

        # Statistics
        self._stats = {
            "total_entities": 0,
            "cui_lookups": 0,
            "text_searches": 0,
            "cache_hits": 0,
            "fallbacks": 0,
            "failures": 0,
            "teo_mappings": 0,
            "domain_skips": 0
        }

        logger.info("CDMMapper initialized (fallback=%s, standard_only=%s, teo_enabled=True, max_workers=%d)",
                   fallback_enabled, standard_only, max_workers)

    def map_entity(self, entity: EnhancedNamedEntity) -> CDMMapResult:
        """
        Map single entity to OMOP CDM concept.

        Args:
            entity: Enhanced named entity with UMLS CUI from Stage 2

        Returns:
            CDMMapResult with OMOP concept and confidence
        """
        self._stats["total_entities"] += 1

        # Route Temporal/Value/Quantity entities to Time Event Ontology
        if entity.domain in ["Temporal", "Value", "Quantity"]:
            return self._map_with_time_event_ontology(entity)

        # Skip entities with unmappable characteristics
        if self._should_skip_ohdsi_api(entity):
            return self._create_skip_result(entity)

        # Check cache first for medical concepts
        cache_key = self._make_cache_key(entity)
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                return self._create_cached_result(entity, cached)

        # Strategy 1: Use UMLS CUI if available
        if entity.umls_cui:
            result = self._map_by_cui(entity)
            if result.omop_concept:
                self._cache_result(cache_key, result)
                return result

        # Strategy 2: Fallback to text search
        if self.fallback_enabled:
            result = self._map_by_text(entity)
            if result.omop_concept:
                self._cache_result(cache_key, result)
                return result

        # Strategy 3: Return entity with placeholder
        self._stats["failures"] += 1
        return CDMMapResult(
            entity=entity,
            omop_concept=None,
            confidence=self.CONFIDENCE_FALLBACK,
            method="fallback",
            error="No OMOP concept found"
        )

    def batch_map_entities(
        self,
        entities: List[EnhancedNamedEntity],
        show_progress: bool = False,
        use_parallel: bool = True
    ) -> List[CDMMapResult]:
        """
        Map multiple entities in batch with parallel processing.

        Args:
            entities: List of enhanced named entities
            show_progress: Print progress during processing
            use_parallel: Enable parallel processing (default: True)

        Returns:
            List of CDM mapping results (order preserved)
        """
        total = len(entities)

        if not use_parallel or total <= 1 or self.max_workers <= 1:
            # Sequential processing (fallback for single entity or disabled parallel)
            results = []
            for i, entity in enumerate(entities, 1):
                if show_progress and i % 10 == 0:
                    print(f"  Mapping {i}/{total} entities...")

                result = self.map_entity(entity)
                results.append(result)

            if show_progress:
                self._print_stats()

            return results

        # Parallel processing with ThreadPoolExecutor
        if show_progress:
            print(f"  Mapping {total} entities in parallel (workers={self.max_workers})...")

        results = [None] * total  # Pre-allocate to preserve order
        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks with their index
            future_to_index = {
                executor.submit(self.map_entity, entity): idx
                for idx, entity in enumerate(entities)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    results[idx] = result
                    completed_count += 1

                    if show_progress and completed_count % 10 == 0:
                        print(f"  Mapped {completed_count}/{total} entities...")

                except Exception as e:
                    logger.error(f"Failed to map entity at index {idx}: {e}")
                    # Create error result
                    results[idx] = CDMMapResult(
                        entity=entities[idx],
                        omop_concept=None,
                        confidence=0.0,
                        method="error",
                        error=str(e)
                    )
                    completed_count += 1

        if show_progress:
            print(f"  ✅ Completed {completed_count}/{total} mappings")
            self._print_stats()

        return results

    def apply_results_to_entities(
        self,
        results: List[CDMMapResult]
    ) -> List[EnhancedNamedEntity]:
        """
        Apply OMOP mapping results to entities.

        Args:
            results: List of CDM mapping results

        Returns:
            List of enhanced entities with OMOP codes
        """
        enhanced_entities = []

        for result in results:
            entity = result.entity
            concept = result.omop_concept

            if concept:
                # Fetch ICD-10CM codes for SNOMED concepts
                icd10cm_codes = []
                if concept.vocabulary_id == "SNOMED":
                    try:
                        icd10cm_codes = self.ohdsi_client.get_icd10cm_codes(concept.concept_id)
                    except Exception as e:
                        logger.warning(f"Failed to fetch ICD-10CM codes for concept {concept.concept_id}: {e}")

                # Prepare metadata with ICD-10CM codes
                metadata = {
                    **(entity.metadata or {}),
                    "omop_concept_id": concept.concept_id,
                    "omop_domain": concept.domain_id,
                    "omop_class": concept.concept_class_id,
                    "mapping_method": result.method,
                    "mapping_confidence": result.confidence
                }

                # Add ICD-10CM codes to metadata if found
                if icd10cm_codes:
                    metadata["icd10cm_codes"] = icd10cm_codes

                # Create new entity with OMOP codes
                enhanced_entity = EnhancedNamedEntity(
                    text=entity.text,
                    type=entity.type,
                    domain=entity.domain,
                    start=entity.start,
                    end=entity.end,
                    confidence=result.confidence,
                    standard_name=concept.concept_name,
                    umls_cui=entity.umls_cui,
                    code_system=concept.vocabulary_id,
                    code_set=[concept.concept_code] if concept.concept_code else None,
                    primary_code=concept.concept_code,
                    metadata=metadata
                )
            else:
                # Keep original entity with error info
                enhanced_entity = EnhancedNamedEntity(
                    text=entity.text,
                    type=entity.type,
                    domain=entity.domain,
                    start=entity.start,
                    end=entity.end,
                    confidence=result.confidence,
                    standard_name=entity.standard_name,
                    umls_cui=entity.umls_cui,
                    code_system=entity.code_system,
                    code_set=entity.code_set,
                    primary_code=entity.primary_code,
                    metadata={
                        **(entity.metadata or {}),
                        "mapping_method": result.method,
                        "mapping_confidence": result.confidence,
                        "mapping_error": result.error
                    }
                )

            enhanced_entities.append(enhanced_entity)

        return enhanced_entities

    def _map_by_cui(self, entity: EnhancedNamedEntity) -> CDMMapResult:
        """Map entity using UMLS CUI."""
        self._stats["cui_lookups"] += 1

        try:
            # Get preferred vocabulary for domain
            vocabulary = self._get_preferred_vocabulary(entity.domain)

            # Search by UMLS concept_name (standard_name from Stage 2)
            search_term = entity.standard_name or entity.text
            concepts = self.ohdsi_client.search_concept(
                term=search_term,
                vocabulary=vocabulary,
                domain=entity.domain,
                standard_only=self.standard_only,
                page_size=5
            )

            if concepts:
                # Return best match (first result)
                best_concept = concepts[0]

                # Validate standard concept
                if self.standard_only and best_concept.standard_concept != 'S':
                    # Try to find "Maps to" standard concept
                    standard_concept = self._resolve_standard_concept(best_concept)
                    if standard_concept:
                        best_concept = standard_concept

                return CDMMapResult(
                    entity=entity,
                    omop_concept=best_concept,
                    confidence=self.CONFIDENCE_CUI_MATCH,
                    method="cui_lookup"
                )

        except Exception as e:
            logger.warning(f"CUI lookup failed for {entity.umls_cui}: {e}")

        return CDMMapResult(
            entity=entity,
            omop_concept=None,
            confidence=0.0,
            method="cui_lookup",
            error="CUI lookup failed"
        )

    def _map_by_text(self, entity: EnhancedNamedEntity) -> CDMMapResult:
        """Fallback: Map entity using text search."""
        self._stats["text_searches"] += 1

        try:
            vocabulary = self._get_preferred_vocabulary(entity.domain)

            # Search by entity text
            concepts = self.ohdsi_client.search_concept(
                term=entity.text,
                vocabulary=vocabulary,
                domain=entity.domain,
                standard_only=self.standard_only,
                page_size=5
            )

            if concepts:
                best_concept = concepts[0]

                # Validate standard concept
                if self.standard_only and best_concept.standard_concept != 'S':
                    standard_concept = self._resolve_standard_concept(best_concept)
                    if standard_concept:
                        best_concept = standard_concept

                return CDMMapResult(
                    entity=entity,
                    omop_concept=best_concept,
                    confidence=self.CONFIDENCE_TEXT_SEARCH,
                    method="text_search"
                )

        except Exception as e:
            logger.warning(f"Text search failed for {entity.text}: {e}")

        self._stats["fallbacks"] += 1
        return CDMMapResult(
            entity=entity,
            omop_concept=None,
            confidence=0.0,
            method="text_search",
            error="Text search failed"
        )

    def _resolve_standard_concept(self, concept: OMOPConcept) -> Optional[OMOPConcept]:
        """
        Resolve non-standard concept to standard concept via "Maps to" relationship.

        Args:
            concept: Non-standard OMOP concept

        Returns:
            Standard OMOP concept or None
        """
        try:
            relationships = self.ohdsi_client.get_concept_relationships(
                concept.concept_id,
                relationship_id="Maps to"
            )

            if relationships:
                # Get first "Maps to" target
                target_concept_id = relationships[0].concept_id_2
                standard_concept = self.ohdsi_client.get_concept_by_id(target_concept_id)

                if standard_concept and standard_concept.standard_concept == 'S':
                    logger.debug(f"Resolved {concept.concept_id} → {standard_concept.concept_id} (standard)")
                    return standard_concept

        except Exception as e:
            logger.warning(f"Failed to resolve standard concept for {concept.concept_id}: {e}")

        return None

    def _get_preferred_vocabulary(self, domain: str) -> Optional[str]:
        """Get preferred OMOP vocabulary for domain."""
        return DEFAULT_VOCABULARIES.get(domain)

    def _make_cache_key(self, entity: EnhancedNamedEntity) -> str:
        """Create cache key for entity."""
        if entity.umls_cui:
            return f"cdm:cui:{entity.umls_cui}:{entity.domain}"
        else:
            normalized_text = entity.text.lower().replace(" ", "_")
            return f"cdm:text:{normalized_text}:{entity.domain}"

    def _create_cached_result(
        self,
        entity: EnhancedNamedEntity,
        cached_data: Dict[str, Any]
    ) -> CDMMapResult:
        """Create CDM result from cached data."""
        omop_concept = None
        if cached_data.get("concept_id"):
            omop_concept = OMOPConcept(
                concept_id=cached_data["concept_id"],
                concept_name=cached_data["concept_name"],
                domain_id=cached_data["domain_id"],
                vocabulary_id=cached_data["vocabulary_id"],
                concept_class_id=cached_data.get("concept_class_id", ""),
                standard_concept=cached_data.get("standard_concept"),
                concept_code=cached_data.get("concept_code", "")
            )

        return CDMMapResult(
            entity=entity,
            omop_concept=omop_concept,
            confidence=cached_data.get("confidence", 0.5),
            method="cached"
        )

    def _cache_result(self, cache_key: str, result: CDMMapResult):
        """Cache mapping result."""
        if not self.cache or not result.omop_concept:
            return

        cached_data = {
            "concept_id": result.omop_concept.concept_id,
            "concept_name": result.omop_concept.concept_name,
            "domain_id": result.omop_concept.domain_id,
            "vocabulary_id": result.omop_concept.vocabulary_id,
            "concept_class_id": result.omop_concept.concept_class_id,
            "standard_concept": result.omop_concept.standard_concept,
            "concept_code": result.omop_concept.concept_code,
            "confidence": result.confidence
        }

        self.cache.set(cache_key, cached_data, ttl=2592000)  # 30 days

    def _map_with_time_event_ontology(self, entity: EnhancedNamedEntity) -> CDMMapResult:
        """
        Map Temporal/Value/Quantity entities using Time Event Ontology.

        Args:
            entity: Entity with domain "Temporal", "Value", or "Quantity"

        Returns:
            CDMMapResult with TEO mapping
        """
        self._stats["teo_mappings"] += 1

        try:
            # Use TimeEventMapper to get TEO codes
            teo_entity = self.time_event_mapper.map_entity(entity)

            # Create pseudo-OMOP concept for TEO
            teo_concept = self._create_teo_concept(teo_entity)

            logger.debug(f"TEO mapped: {entity.text} → {teo_concept.concept_code}")

            return CDMMapResult(
                entity=teo_entity,
                omop_concept=teo_concept,
                confidence=teo_entity.confidence or 0.95,
                method="time_event_ontology"
            )

        except Exception as e:
            logger.warning(f"TEO mapping failed for '{entity.text}': {e}")
            self._stats["failures"] += 1
            return CDMMapResult(
                entity=entity,
                omop_concept=None,
                confidence=0.0,
                method="teo_failed",
                error=str(e)
            )

    def _should_skip_ohdsi_api(self, entity: EnhancedNamedEntity) -> bool:
        """
        Check if entity should skip OHDSI API call.

        Args:
            entity: Entity to check

        Returns:
            True if entity should be skipped
        """
        text = entity.text.strip()

        # Skip if contains special comparison operators (safety check)
        if any(op in text for op in ["≥", "≤", ">", "<", "±", "%"]):
            logger.debug(f"Skipping OHDSI API for entity with special chars: {text}")
            return True

        # Skip Provider/Negation_cue domains
        if entity.domain in ["Provider", "Negation_cue"]:
            logger.debug(f"Skipping OHDSI API for {entity.domain} domain: {text}")
            return True

        return False

    def _create_skip_result(self, entity: EnhancedNamedEntity) -> CDMMapResult:
        """
        Create result for skipped entities.

        Args:
            entity: Entity that was skipped

        Returns:
            CDMMapResult with skip information
        """
        self._stats["domain_skips"] += 1

        return CDMMapResult(
            entity=entity,
            omop_concept=None,
            confidence=0.0,
            method="domain_skip",
            error=f"Entity domain '{entity.domain}' does not require OMOP mapping"
        )

    def _create_teo_concept(self, teo_entity: EnhancedNamedEntity) -> OMOPConcept:
        """
        Create pseudo-OMOP concept for TEO-mapped entity.

        Args:
            teo_entity: Entity with TEO mapping

        Returns:
            OMOPConcept with TEO vocabulary
        """
        # Generate concept_id from TEO code hash
        teo_code = teo_entity.primary_code or "TEO:UNKNOWN"
        concept_id = abs(hash(teo_code)) % 1000000 + 2000000000  # 2B+ range for TEO

        return OMOPConcept(
            concept_id=concept_id,
            concept_name=teo_entity.standard_name or teo_entity.text,
            domain_id=teo_entity.domain,
            vocabulary_id="TEO",
            concept_class_id="Time Event",
            standard_concept="S",
            concept_code=teo_code,
            metadata=teo_entity.metadata or {}
        )

    def _print_stats(self):
        """Print mapping statistics."""
        stats = self._stats
        total = stats["total_entities"]

        print(f"\n📊 CDM Mapping Statistics:")
        print(f"  - Total entities: {total}")
        print(f"  - TEO mappings: {stats['teo_mappings']} ({stats['teo_mappings']/max(total,1)*100:.1f}%)")
        print(f"  - CUI lookups: {stats['cui_lookups']} ({stats['cui_lookups']/max(total,1)*100:.1f}%)")
        print(f"  - Text searches: {stats['text_searches']} ({stats['text_searches']/max(total,1)*100:.1f}%)")
        print(f"  - Cache hits: {stats['cache_hits']} ({stats['cache_hits']/max(total,1)*100:.1f}%)")
        print(f"  - Domain skips: {stats['domain_skips']} ({stats['domain_skips']/max(total,1)*100:.1f}%)")
        print(f"  - Fallbacks: {stats['fallbacks']} ({stats['fallbacks']/max(total,1)*100:.1f}%)")
        print(f"  - Failures: {stats['failures']} ({stats['failures']/max(total,1)*100:.1f}%)")

    def get_stats(self) -> Dict[str, int]:
        """Get mapping statistics."""
        return dict(self._stats)


__all__ = ["CDMMapper", "CDMMapResult"]
