"""
API-Based Standardizer for Trialist Stage 2: Component Standardization

Provides concept normalization and standardization using:
1. UMLS API for CUI lookup and preferred terms
2. OHDSI WebAPI for OMOP CDM concept mapping
3. Offline fallback for reliability
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, Tuple

from .trialist_models import EnhancedNamedEntity, TemporalRelation
from .clients import UMLSClient, OHDSIClient, CacheManager
from .clients.umls_client import UMLSConcept
from .clients.ohdsi_client import OMOPConcept
from .offline_standardizer import OfflineStandardizer

logger = logging.getLogger(__name__)


class APIStandardizer:
    """
    API-based medical concept standardizer using UMLS and OHDSI services.

    Workflow:
    1. Expand abbreviations (local)
    2. Check cache (local, <10ms)
    3. UMLS API search (remote, ~500ms) → CUI + preferred name
    4. OHDSI API mapping (remote, ~500ms) → OMOP concept_id + codes
    5. Cache result (local)
    6. Fallback to OfflineStandardizer on failure

    Features:
    - Real UMLS CUIs and preferred terms
    - Real OMOP concept IDs and vocabulary codes (SNOMED, ICD-10, RxNorm, LOINC)
    - Intelligent caching for performance
    - Offline fallback for reliability
    - Batch processing with deduplication

    Usage:
        >>> umls_client = UMLSClient(api_key="your_key")
        >>> ohdsi_client = OHDSIClient()
        >>> cache = CacheManager()
        >>> standardizer = APIStandardizer(umls_client, ohdsi_client, cache)
        >>> entity = EnhancedNamedEntity(text="MI", domain="Condition")
        >>> result = standardizer.standardize_entity(entity)
        >>> print(result.umls_cui)  # "C0027051"
        >>> print(result.primary_code)  # "22298006" (SNOMED)
    """

    def __init__(
        self,
        umls_client: UMLSClient,
        ohdsi_client: OHDSIClient,
        cache_manager: CacheManager,
        fallback_to_offline: bool = True,
        offline_standardizer: Optional[OfflineStandardizer] = None,
        max_workers: int = 10
    ):
        """
        Initialize API-based standardizer.

        Args:
            umls_client: UMLS API client
            ohdsi_client: OHDSI WebAPI client
            cache_manager: Cache manager for performance
            fallback_to_offline: Use offline standardizer on API failure
            offline_standardizer: Custom offline standardizer (or default)
            max_workers: Maximum parallel workers for batch processing
        """
        self.umls_client = umls_client
        self.ohdsi_client = ohdsi_client
        self.cache = cache_manager
        self.fallback_to_offline = fallback_to_offline
        self.offline = offline_standardizer or OfflineStandardizer()
        self.max_workers = max_workers

        # Statistics
        self.stats = {
            "umls_requests": 0,
            "ohdsi_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fallback_count": 0,
            "total_entities": 0
        }

        logger.info("APIStandardizer initialized with UMLS and OHDSI clients")

    def standardize_entity(self, entity: EnhancedNamedEntity) -> EnhancedNamedEntity:
        """
        Standardize a single entity using UMLS + OHDSI APIs with fallback.

        Workflow:
        1. Expand abbreviations (e.g., "MI" → "myocardial infarction")
        2. Check cache for previous result
        3. UMLS API: Search for CUI and preferred term
        4. OHDSI API: Map to standard OMOP concept and codes
        5. Cache successful result
        6. On failure: Fallback to OfflineStandardizer

        Args:
            entity: Entity to standardize

        Returns:
            Enhanced entity with standardization information
        """
        self.stats["total_entities"] += 1

        # Step 1: Expand abbreviations
        expanded_text = self.offline._expand_abbreviations(entity.text)

        # Step 2: Check cache
        cache_key = self._build_cache_key(expanded_text, entity.domain)
        cached_result = self.cache.get(cache_key)

        if cached_result:
            self.stats["cache_hits"] += 1
            logger.debug(f"Cache hit for: {entity.text}")
            return self._apply_cached_result(entity, cached_result)

        self.stats["cache_misses"] += 1

        # Step 3: Try API-based standardization
        try:
            result = self._standardize_with_apis(entity, expanded_text)

            # Step 5: Cache successful result
            self.cache.set(cache_key, result, ttl=7*24*3600)  # 7 days

            return result

        except Exception as e:
            logger.warning(f"API standardization failed for '{entity.text}': {e}")
            self.stats["fallback_count"] += 1

            # Step 6: Fallback to offline standardizer
            if self.fallback_to_offline:
                logger.info(f"Falling back to offline standardizer for: {entity.text}")
                return self.offline.standardize_entity(entity)
            else:
                raise

    def batch_standardize(
        self,
        entities: List[EnhancedNamedEntity],
        show_progress: bool = False
    ) -> List[EnhancedNamedEntity]:
        """
        Standardize multiple entities with optimization.

        Optimizations:
        1. Deduplication: Same text processed only once
        2. Parallel processing: Multiple API calls concurrently
        3. Cache reuse: Cached results used immediately

        Args:
            entities: List of entities to standardize
            show_progress: Show progress bar (requires tqdm)

        Returns:
            List of standardized entities
        """
        if not entities:
            return []

        logger.info(f"Batch standardizing {len(entities)} entities")
        start_time = time.time()

        # Step 1: Deduplicate by text + domain
        unique_entities: Dict[Tuple[str, str], EnhancedNamedEntity] = {}
        entity_map: Dict[int, Tuple[str, str]] = {}  # Index → (text, domain)

        for i, entity in enumerate(entities):
            key = (entity.text.lower(), entity.domain)
            entity_map[i] = key
            if key not in unique_entities:
                unique_entities[key] = entity

        logger.info(f"Deduplication: {len(entities)} → {len(unique_entities)} unique entities")

        # Step 2: Process unique entities in parallel
        results: Dict[Tuple[str, str], EnhancedNamedEntity] = {}

        if show_progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(unique_entities.items(), desc="Standardizing")
            except ImportError:
                logger.warning("tqdm not installed, progress bar disabled")
                iterator = unique_entities.items()
        else:
            iterator = unique_entities.items()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_key = {
                executor.submit(self.standardize_entity, entity): key
                for key, entity in iterator
            }

            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    result = future.result()
                    results[key] = result
                except Exception as e:
                    logger.error(f"Failed to standardize {key}: {e}")
                    # Use original entity on failure
                    results[key] = unique_entities[key]

        # Step 3: Map results back to original order
        standardized_entities = []
        for i, entity in enumerate(entities):
            key = entity_map[i]
            standardized_entity = results.get(key, entity)
            standardized_entities.append(standardized_entity)

        elapsed = time.time() - start_time
        logger.info(f"Batch standardization completed in {elapsed:.2f}s")
        self._log_stats()

        return standardized_entities

    def standardize_temporal_relation(self, text: str) -> Optional[TemporalRelation]:
        """
        Standardize temporal expressions.

        Uses offline pattern matching (no API calls needed).

        Args:
            text: Text containing temporal relationship

        Returns:
            Standardized temporal relation or None if not found
        """
        return self.offline.standardize_temporal_relation(text)

    def _standardize_with_apis(
        self,
        entity: EnhancedNamedEntity,
        expanded_text: str
    ) -> EnhancedNamedEntity:
        """
        Perform API-based standardization using UMLS + OHDSI.

        Args:
            entity: Original entity
            expanded_text: Expanded text (abbreviations expanded)

        Returns:
            Standardized entity with real codes

        Raises:
            Exception: If API calls fail
        """
        # Step 1: UMLS API search
        umls_result = self._search_umls(expanded_text, entity.domain)
        if not umls_result:
            raise ValueError(f"UMLS search returned no results for: {expanded_text}")

        # Step 2: OHDSI API mapping
        ohdsi_result = self._map_to_ohdsi(umls_result, entity.domain)

        # Step 3: Combine results
        return self._combine_api_results(entity, umls_result, ohdsi_result, expanded_text)

    def _search_umls(self, text: str, domain: str) -> Optional[UMLSConcept]:
        """
        Search UMLS API for concept.

        Args:
            text: Search term
            domain: Entity domain for filtering

        Returns:
            Best matching UMLS concept or None
        """
        try:
            self.stats["umls_requests"] += 1

            # Map domain to UMLS semantic types
            semantic_types = self._map_domain_to_semantic_types(domain)

            # Search UMLS
            concepts = self.umls_client.search_concept(
                text,
                search_type="words",
                page_size=5,
                source_vocabularies=None
            )

            if not concepts:
                logger.debug(f"UMLS: No results for '{text}'")
                return None

            # Filter by semantic types if available
            if semantic_types:
                filtered = [
                    c for c in concepts
                    if any(st in c.semantic_types for st in semantic_types)
                ]
                if filtered:
                    concepts = filtered

            # Return highest confidence result
            best_concept = max(concepts, key=lambda c: c.confidence)
            logger.debug(f"UMLS: Found '{best_concept.preferred_name}' (CUI: {best_concept.cui})")

            return best_concept

        except Exception as e:
            logger.error(f"UMLS search failed for '{text}': {e}")
            return None

    def _map_to_ohdsi(
        self,
        umls_concept: UMLSConcept,
        domain: str
    ) -> Optional[OMOPConcept]:
        """
        Map UMLS concept to OHDSI OMOP concept.

        Args:
            umls_concept: UMLS concept to map
            domain: Entity domain for vocabulary selection

        Returns:
            OMOP concept with standard codes or None
        """
        try:
            self.stats["ohdsi_requests"] += 1

            # Map domain to OMOP vocabularies
            vocabularies = self._map_domain_to_vocabularies(domain)

            # Try searching by preferred name first
            concepts = self.ohdsi_client.search_concept(
                umls_concept.preferred_name,
                vocabulary=vocabularies[0] if vocabularies else None,
                domain=self._map_domain_to_omop_domain(domain),
                page_size=3,
                standard_only=True
            )

            if concepts:
                best_concept = concepts[0]
                logger.debug(
                    f"OHDSI: Mapped to '{best_concept.concept_name}' "
                    f"(ID: {best_concept.concept_id}, Code: {best_concept.concept_code})"
                )
                return best_concept

            # Try searching by CUI if available
            if umls_concept.cui:
                concepts = self.ohdsi_client.search_concept(
                    umls_concept.cui,
                    page_size=3,
                    standard_only=True
                )

                if concepts:
                    return concepts[0]

            logger.debug(f"OHDSI: No standard concept found for '{umls_concept.preferred_name}'")
            return None

        except Exception as e:
            logger.error(f"OHDSI mapping failed for CUI {umls_concept.cui}: {e}")
            return None

    def _combine_api_results(
        self,
        entity: EnhancedNamedEntity,
        umls_concept: UMLSConcept,
        ohdsi_concept: Optional[OMOPConcept],
        expanded_text: str
    ) -> EnhancedNamedEntity:
        """
        Combine UMLS and OHDSI results into standardized entity.

        Args:
            entity: Original entity
            umls_concept: UMLS concept result
            ohdsi_concept: OHDSI concept result (optional)
            expanded_text: Expanded text

        Returns:
            Standardized entity with combined information
        """
        # Determine primary code and code system
        if ohdsi_concept:
            primary_code = ohdsi_concept.concept_code
            code_system = ohdsi_concept.vocabulary_id

            # Get additional vocabulary codes if available
            code_set = [primary_code]
            try:
                vocab_codes = self.ohdsi_client.get_vocabulary_codes(
                    ohdsi_concept.concept_id,
                    target_vocabularies=self._map_domain_to_vocabularies(entity.domain)
                )
                code_set.extend([code for code in vocab_codes.values() if code != primary_code])
            except Exception as e:
                logger.warning(f"Failed to get vocabulary codes: {e}")
        else:
            # UMLS only (no OHDSI mapping)
            primary_code = None
            code_system = self.offline.domain_vocabularies.get(entity.domain, ["Unknown"])[0]
            code_set = []

        # Build metadata
        metadata = {
            **(entity.metadata or {}),
            'standardization': {
                'method': 'api_umls_ohdsi' if ohdsi_concept else 'api_umls_only',
                'confidence': umls_concept.confidence,
                'original_text': entity.text,
                'expanded_text': expanded_text,
                'umls_search_result': {
                    'cui': umls_concept.cui,
                    'preferred_name': umls_concept.preferred_name,
                    'semantic_types': umls_concept.semantic_types,
                    'synonyms': umls_concept.synonyms[:5] if umls_concept.synonyms else []
                }
            }
        }

        if ohdsi_concept:
            metadata['standardization']['ohdsi_concept_id'] = ohdsi_concept.concept_id
            metadata['standardization']['ohdsi_concept_name'] = ohdsi_concept.concept_name
            metadata['standardization']['vocabularies'] = {
                code_system: primary_code
            }

        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=umls_concept.confidence,
            # Standardization fields
            standard_name=umls_concept.preferred_name,
            umls_cui=umls_concept.cui,
            code_system=code_system,
            code_set=code_set if code_set else None,
            primary_code=primary_code,
            metadata=metadata
        )

    def _apply_cached_result(
        self,
        entity: EnhancedNamedEntity,
        cached_data: Dict[str, Any]
    ) -> EnhancedNamedEntity:
        """
        Apply cached standardization result to entity.

        Args:
            entity: Original entity
            cached_data: Cached standardization data

        Returns:
            Entity with cached standardization applied
        """
        return EnhancedNamedEntity(
            text=entity.text,
            type=entity.type,
            domain=entity.domain,
            start=entity.start,
            end=entity.end,
            confidence=cached_data.get("confidence", entity.confidence),
            standard_name=cached_data.get("standard_name"),
            umls_cui=cached_data.get("umls_cui"),
            code_system=cached_data.get("code_system"),
            code_set=cached_data.get("code_set"),
            primary_code=cached_data.get("primary_code"),
            metadata={
                **(entity.metadata or {}),
                'standardization': {
                    **cached_data.get("standardization", {}),
                    'from_cache': True
                }
            }
        )

    def _build_cache_key(self, text: str, domain: str) -> str:
        """Build cache key for text and domain."""
        normalized_text = text.lower().strip()
        return f"api_std:{domain}:{normalized_text}"

    def _map_domain_to_semantic_types(self, domain: str) -> List[str]:
        """Map entity domain to UMLS semantic types for filtering."""
        mapping = {
            "Condition": [
                "Disease or Syndrome",
                "Neoplastic Process",
                "Pathologic Function",
                "Sign or Symptom"
            ],
            "Drug": [
                "Pharmacologic Substance",
                "Antibiotic",
                "Clinical Drug",
                "Amino Acid, Peptide, or Protein"
            ],
            "Measurement": [
                "Laboratory Procedure",
                "Diagnostic Procedure",
                "Clinical Attribute"
            ],
            "Procedure": [
                "Therapeutic or Preventive Procedure",
                "Diagnostic Procedure",
                "Surgical Procedure"
            ],
            "Device": [
                "Medical Device",
                "Clinical Drug"
            ],
            "Observation": [
                "Finding",
                "Clinical Attribute"
            ],
            "Demographic": [
                "Organism Attribute",
                "Population Group"
            ]
        }
        return mapping.get(domain, [])

    def _map_domain_to_vocabularies(self, domain: str) -> List[str]:
        """Map entity domain to OMOP vocabularies."""
        return self.offline.domain_vocabularies.get(domain, ["SNOMED"])

    def _map_domain_to_omop_domain(self, domain: str) -> str:
        """Map entity domain to OMOP CDM domain."""
        mapping = {
            "Condition": "Condition",
            "Drug": "Drug",
            "Measurement": "Measurement",
            "Procedure": "Procedure",
            "Device": "Device",
            "Observation": "Observation",
            "Visit": "Visit",
            "Demographic": "Observation"  # Demographics stored as observations
        }
        return mapping.get(domain, "Observation")

    def _log_stats(self):
        """Log standardization statistics."""
        stats = self.stats
        total = stats["total_entities"]

        if total == 0:
            return

        cache_hit_rate = stats["cache_hits"] / total * 100
        fallback_rate = stats["fallback_count"] / total * 100

        logger.info(
            f"Standardization stats: "
            f"Total={total}, "
            f"UMLS requests={stats['umls_requests']}, "
            f"OHDSI requests={stats['ohdsi_requests']}, "
            f"Cache hits={stats['cache_hits']} ({cache_hit_rate:.1f}%), "
            f"Fallbacks={stats['fallback_count']} ({fallback_rate:.1f}%)"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get current standardization statistics."""
        return dict(self.stats)

    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            "umls_requests": 0,
            "ohdsi_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fallback_count": 0,
            "total_entities": 0
        }


__all__ = ["APIStandardizer"]
