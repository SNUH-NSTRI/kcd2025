"""
OHDSI WebAPI Client

Provides access to OHDSI Athena vocabulary service for OMOP CDM concept
mapping and standardization.

API Documentation: http://webapidoc.ohdsi.org/
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class OMOPConcept:
    """OMOP CDM Concept representation."""

    concept_id: int
    """Unique OMOP concept identifier (e.g., 312327)"""

    concept_name: str
    """Concept name (e.g., Myocardial infarction)"""

    domain_id: str
    """Domain classification (e.g., Condition, Drug, Measurement)"""

    vocabulary_id: str
    """Source vocabulary (e.g., SNOMED, ICD10CM, RxNorm, LOINC)"""

    concept_class_id: str
    """Concept class (e.g., Clinical Finding, Ingredient)"""

    standard_concept: Optional[str] = None
    """'S' for standard, 'C' for classification, None for non-standard"""

    concept_code: str = ""
    """Vocabulary-specific code (e.g., 22298006 for SNOMED)"""

    valid_start_date: Optional[str] = None
    """Concept validity start date"""

    valid_end_date: Optional[str] = None
    """Concept validity end date"""

    invalid_reason: Optional[str] = None
    """Reason for invalidity if applicable"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata from OHDSI"""


@dataclass
class ConceptRelationship:
    """OMOP CDM Concept Relationship."""

    relationship_id: str
    """Relationship type (e.g., 'Maps to', 'Is a', 'Subsumes')"""

    concept_id_1: int
    """Source concept ID"""

    concept_id_2: int
    """Target concept ID"""

    valid_start_date: Optional[str] = None
    """Relationship validity start date"""

    valid_end_date: Optional[str] = None
    """Relationship validity end date"""

    invalid_reason: Optional[str] = None
    """Reason for invalidity if applicable"""


class OHDSIClient:
    """
    Client for OHDSI WebAPI.

    Provides methods to search OMOP vocabularies, map concepts, and
    access standardized medical terminologies.

    Usage:
        >>> client = OHDSIClient(base_url="http://api.ohdsi.org/WebAPI")
        >>> concepts = client.search_concept("diabetes", vocabulary="SNOMED")
        >>> if concepts:
        ...     details = client.get_concept_by_id(concepts[0].concept_id)
    """

    # Public OHDSI API instance
    DEFAULT_BASE_URL = "http://api.ohdsi.org/WebAPI"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 5,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        api_key: Optional[str] = None,
        rate_limit: float = 0.05
    ):
        """
        Initialize OHDSI client.

        Args:
            base_url: WebAPI base URL (default: public OHDSI instance)
            timeout: Request timeout in seconds (default: 5s, reduced from 10s)
            max_retries: Maximum number of retry attempts (default: 2, reduced from 3)
            retry_backoff: Exponential backoff factor for retries (default: 0.5s)
            api_key: Optional API key for authenticated instances
            rate_limit: Minimum interval between requests in seconds (default: 0.05s = 20 req/s)
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.api_key = api_key

        # Configure session with retry logic
        self.session = self._create_session()

        # Rate limiting - optimized for parallel requests
        self._last_request_time = 0.0
        self._min_request_interval = rate_limit  # Configurable rate limit

        logger.info(f"OHDSI Client initialized: {self.base_url} (timeout={timeout}s, rate_limit={rate_limit}s)")

    def _create_session(self) -> requests.Session:
        """Create requests session with retry configuration."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Add API key to headers if provided
        if self.api_key:
            session.headers.update({"Authorization": f"Bearer {self.api_key}"})

        session.headers.update({"Accept": "application/json"})

        return session

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to OHDSI WebAPI.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            requests.HTTPError: If request fails
        """
        self._rate_limit()

        url = f"{self.base_url}/{endpoint}"

        logger.debug(f"OHDSI API Request: {endpoint} with params: {params}")

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"OHDSI API Response: {len(data) if isinstance(data, list) else 'single'} result(s)")

            return data

        except requests.exceptions.Timeout as e:
            logger.error(f"OHDSI API timeout: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"OHDSI API HTTP error: {e}")
            if e.response.status_code == 401:
                raise ValueError("Invalid OHDSI API credentials") from e
            elif e.response.status_code == 429:
                raise RuntimeError("OHDSI API rate limit exceeded") from e
            raise
        except Exception as e:
            logger.error(f"OHDSI API request failed: {e}")
            raise

    def search_concept(
        self,
        term: str,
        vocabulary: Optional[str] = None,
        domain: Optional[str] = None,
        page_size: int = 10,
        standard_only: bool = False
    ) -> List[OMOPConcept]:
        """
        Search for OMOP concepts by term.

        Args:
            term: Search term (e.g., "diabetes", "metformin")
            vocabulary: Filter by vocabulary (e.g., "SNOMED", "ICD10CM", "RxNorm")
            domain: Filter by domain (e.g., "Condition", "Drug", "Measurement")
            page_size: Number of results to return (max 100)
            standard_only: Return only standard concepts

        Returns:
            List of OMOP concepts matching the search term

        Example:
            >>> concepts = client.search_concept("myocardial infarction", vocabulary="SNOMED")
            >>> concepts[0].concept_id
            312327
            >>> concepts[0].concept_name
            'Myocardial infarction'
        """
        if not term or not term.strip():
            return []

        # URL encode the search term
        encoded_term = quote(term.strip())

        try:
            # OHDSI WebAPI vocabulary search endpoint
            data = self._make_request(f"vocabulary/search/{encoded_term}")

            # Parse response
            concepts = []
            results = data if isinstance(data, list) else [data]

            for item in results:
                # Handle nested 'concept' structure
                concept_data = item.get("concept", item)

                # Apply filters
                if vocabulary and concept_data.get("VOCABULARY_ID") != vocabulary:
                    continue

                if domain and concept_data.get("DOMAIN_ID") != domain:
                    continue

                if standard_only and concept_data.get("STANDARD_CONCEPT") != "S":
                    continue

                concept = OMOPConcept(
                    concept_id=concept_data.get("CONCEPT_ID", 0),
                    concept_name=concept_data.get("CONCEPT_NAME", ""),
                    domain_id=concept_data.get("DOMAIN_ID", ""),
                    vocabulary_id=concept_data.get("VOCABULARY_ID", ""),
                    concept_class_id=concept_data.get("CONCEPT_CLASS_ID", ""),
                    standard_concept=concept_data.get("STANDARD_CONCEPT"),
                    concept_code=concept_data.get("CONCEPT_CODE", ""),
                    valid_start_date=concept_data.get("VALID_START_DATE"),
                    valid_end_date=concept_data.get("VALID_END_DATE"),
                    invalid_reason=concept_data.get("INVALID_REASON"),
                    metadata={
                        "search_term": term,
                        "invalid_reason_caption": concept_data.get("INVALID_REASON_CAPTION"),
                        "standard_concept_caption": concept_data.get("STANDARD_CONCEPT_CAPTION")
                    }
                )
                concepts.append(concept)

                if len(concepts) >= page_size:
                    break

            logger.info(f"Found {len(concepts)} OMOP concepts for term: '{term}'")
            return concepts

        except Exception as e:
            logger.error(f"Search failed for term '{term}': {e}")
            return []

    def get_concept_by_id(self, concept_id: int) -> Optional[OMOPConcept]:
        """
        Get detailed information for a concept ID.

        Args:
            concept_id: OMOP concept identifier

        Returns:
            Detailed OMOP concept or None if not found

        Example:
            >>> concept = client.get_concept_by_id(312327)
            >>> concept.concept_name
            'Myocardial infarction'
            >>> concept.vocabulary_id
            'SNOMED'
        """
        if not concept_id or concept_id <= 0:
            logger.warning(f"Invalid concept ID: {concept_id}")
            return None

        try:
            data = self._make_request(f"vocabulary/concept/{concept_id}")

            # Handle response format
            concept_data = data.get("concept", data) if isinstance(data, dict) else data

            concept = OMOPConcept(
                concept_id=concept_data.get("CONCEPT_ID", concept_id),
                concept_name=concept_data.get("CONCEPT_NAME", ""),
                domain_id=concept_data.get("DOMAIN_ID", ""),
                vocabulary_id=concept_data.get("VOCABULARY_ID", ""),
                concept_class_id=concept_data.get("CONCEPT_CLASS_ID", ""),
                standard_concept=concept_data.get("STANDARD_CONCEPT"),
                concept_code=concept_data.get("CONCEPT_CODE", ""),
                valid_start_date=concept_data.get("VALID_START_DATE"),
                valid_end_date=concept_data.get("VALID_END_DATE"),
                invalid_reason=concept_data.get("INVALID_REASON"),
                metadata={
                    "invalid_reason_caption": concept_data.get("INVALID_REASON_CAPTION"),
                    "standard_concept_caption": concept_data.get("STANDARD_CONCEPT_CAPTION")
                }
            )

            logger.info(f"Retrieved concept: {concept_id}")
            return concept

        except Exception as e:
            logger.error(f"Failed to get concept {concept_id}: {e}")
            return None

    def get_concept_relationships(
        self,
        concept_id: int,
        relationship_type: Optional[str] = None
    ) -> List[ConceptRelationship]:
        """
        Get relationships for a concept.

        Args:
            concept_id: OMOP concept identifier
            relationship_type: Filter by relationship (e.g., "Maps to", "Is a")

        Returns:
            List of concept relationships

        Example:
            >>> relationships = client.get_concept_relationships(312327, "Maps to")
            >>> relationships[0].concept_id_2  # Target concept
            4329847
        """
        if not concept_id or concept_id <= 0:
            return []

        try:
            data = self._make_request(f"vocabulary/concept/{concept_id}/related")

            relationships = []
            results = data if isinstance(data, list) else data.get("relationships", [])

            for item in results:
                rel_id = item.get("RELATIONSHIP_ID", "")

                # Apply filter
                if relationship_type and rel_id != relationship_type:
                    continue

                relationship = ConceptRelationship(
                    relationship_id=rel_id,
                    concept_id_1=item.get("CONCEPT_ID_1", concept_id),
                    concept_id_2=item.get("CONCEPT_ID_2", 0),
                    valid_start_date=item.get("VALID_START_DATE"),
                    valid_end_date=item.get("VALID_END_DATE"),
                    invalid_reason=item.get("INVALID_REASON")
                )
                relationships.append(relationship)

            logger.debug(f"Found {len(relationships)} relationships for concept: {concept_id}")
            return relationships

        except Exception as e:
            logger.error(f"Failed to get relationships for concept {concept_id}: {e}")
            return []

    def map_to_standard(
        self,
        source_code: str,
        vocabulary: str
    ) -> Optional[OMOPConcept]:
        """
        Map a source code to its standard OMOP concept.

        Args:
            source_code: Source vocabulary code (e.g., "I21.9" for ICD-10)
            vocabulary: Source vocabulary (e.g., "ICD10CM", "ICD10")

        Returns:
            Standard OMOP concept or None if mapping not found

        Example:
            >>> concept = client.map_to_standard("I21.9", "ICD10CM")
            >>> concept.concept_id
            312327
            >>> concept.vocabulary_id
            'SNOMED'
        """
        if not source_code or not vocabulary:
            return None

        try:
            # First, search for the source concept
            concepts = self.search_concept(
                source_code,
                vocabulary=vocabulary,
                page_size=1
            )

            if not concepts:
                logger.warning(f"Source code not found: {source_code} in {vocabulary}")
                return None

            source_concept = concepts[0]

            # If already standard, return it
            if source_concept.standard_concept == "S":
                return source_concept

            # Get relationships to find "Maps to" standard concept
            relationships = self.get_concept_relationships(
                source_concept.concept_id,
                relationship_type="Maps to"
            )

            if not relationships:
                logger.warning(f"No 'Maps to' relationship found for concept: {source_concept.concept_id}")
                return source_concept  # Return non-standard as fallback

            # Get the mapped standard concept
            standard_concept_id = relationships[0].concept_id_2
            standard_concept = self.get_concept_by_id(standard_concept_id)

            if standard_concept:
                logger.info(f"Mapped {source_code} ({vocabulary}) to concept: {standard_concept_id}")
                return standard_concept
            else:
                return source_concept

        except Exception as e:
            logger.error(f"Failed to map {source_code} ({vocabulary}): {e}")
            return None

    def get_vocabulary_codes(
        self,
        concept_id: int,
        target_vocabularies: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Get vocabulary-specific codes for a concept.

        Args:
            concept_id: OMOP concept identifier
            target_vocabularies: List of vocabularies to retrieve (e.g., ["ICD10CM", "SNOMED"])

        Returns:
            Dictionary mapping vocabulary to code

        Example:
            >>> codes = client.get_vocabulary_codes(312327, ["ICD10CM", "SNOMED", "RxNorm"])
            >>> codes
            {'SNOMED': '22298006', 'ICD10CM': 'I21.9'}
        """
        if not concept_id or concept_id <= 0:
            return {}

        try:
            # Get concept details
            concept = self.get_concept_by_id(concept_id)
            if not concept:
                return {}

            codes = {}

            # Add primary code
            if not target_vocabularies or concept.vocabulary_id in target_vocabularies:
                codes[concept.vocabulary_id] = concept.concept_code

            # Get related concepts in different vocabularies
            relationships = self.get_concept_relationships(concept_id)

            for rel in relationships:
                if rel.relationship_id in ["Maps to", "Mapped from"]:
                    related_concept = self.get_concept_by_id(rel.concept_id_2)

                    if related_concept:
                        vocab = related_concept.vocabulary_id
                        if not target_vocabularies or vocab in target_vocabularies:
                            codes[vocab] = related_concept.concept_code

            logger.debug(f"Retrieved {len(codes)} vocabulary codes for concept: {concept_id}")
            return codes

        except Exception as e:
            logger.error(f"Failed to get vocabulary codes for concept {concept_id}: {e}")
            return {}

    def get_icd10cm_codes(
        self,
        concept_id: int
    ) -> List[str]:
        """
        Get ICD-10CM codes for a SNOMED concept using OHDSI concept_relationship.

        This method maps SNOMED CT concepts to ICD-10CM codes by querying
        the concept_relationship table for "Maps to" relationships.

        Args:
            concept_id: OMOP concept identifier (typically SNOMED)

        Returns:
            List of ICD-10CM codes (may be empty if no mapping exists)

        Example:
            >>> icd_codes = client.get_icd10cm_codes(4216914)  # SNOMED: 30-day mortality
            >>> icd_codes
            ['R99']  # ICD-10CM: Ill-defined cause of mortality
        """
        if not concept_id or concept_id <= 0:
            return []

        try:
            # Strategy 1: Get related concepts via relationships
            relationships = self.get_concept_relationships(concept_id)

            icd_codes = []
            for rel in relationships:
                # Look for "Maps to" or "Mapped from" relationships
                if rel.relationship_id in ["Maps to", "Mapped from"]:
                    # Get the target concept details
                    related_concept = self.get_concept_by_id(rel.concept_id_2)

                    if related_concept and related_concept.vocabulary_id == "ICD10CM":
                        icd_codes.append(related_concept.concept_code)

            if icd_codes:
                logger.debug(f"Found {len(icd_codes)} ICD-10CM codes for concept {concept_id}: {icd_codes}")
                return icd_codes

            # Strategy 2: Use get_vocabulary_codes as fallback
            vocab_codes = self.get_vocabulary_codes(concept_id, target_vocabularies=["ICD10CM"])
            if "ICD10CM" in vocab_codes:
                logger.debug(f"Found ICD-10CM code via vocabulary lookup: {vocab_codes['ICD10CM']}")
                return [vocab_codes["ICD10CM"]]

            logger.debug(f"No ICD-10CM mapping found for concept {concept_id}")
            return []

        except Exception as e:
            logger.error(f"Failed to get ICD-10CM codes for concept {concept_id}: {e}")
            return []


__all__ = ["OHDSIClient", "OMOPConcept", "ConceptRelationship"]
