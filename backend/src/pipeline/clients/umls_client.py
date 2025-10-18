"""
UMLS REST API Client

Provides access to the Unified Medical Language System (UMLS) for medical concept
standardization and terminology mapping.

API Documentation: https://documentation.uts.nlm.nih.gov/rest/home.html
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
class UMLSConcept:
    """UMLS Concept representation."""

    cui: str
    """Concept Unique Identifier (e.g., C0027051)"""

    preferred_name: str
    """Preferred name in UMLS (e.g., Myocardial infarction)"""

    semantic_types: List[str] = field(default_factory=list)
    """Semantic types (e.g., ['Disease or Syndrome'])"""

    synonyms: List[str] = field(default_factory=list)
    """Alternative names and synonyms"""

    definitions: List[str] = field(default_factory=list)
    """Medical definitions from various sources"""

    source_vocabularies: List[str] = field(default_factory=list)
    """Source vocabularies containing this concept (e.g., ['SNOMED CT', 'ICD10CM'])"""

    confidence: float = 1.0
    """Match confidence score (0.0-1.0)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata from UMLS"""


class UMLSClient:
    """
    Client for UMLS REST API.

    Provides methods to search medical concepts, retrieve CUI details,
    and access UMLS terminology mappings.

    Usage:
        >>> client = UMLSClient(api_key="your_api_key")
        >>> concepts = client.search_concept("heart attack", search_type="words")
        >>> if concepts:
        ...     cui_details = client.get_cui_details(concepts[0].cui)
    """

    BASE_URL = "https://uts-ws.nlm.nih.gov/rest"
    VERSION = "current"

    def __init__(
        self,
        api_key: str,
        timeout: int = 10,
        max_retries: int = 3,
        retry_backoff: float = 1.0
    ):
        """
        Initialize UMLS client.

        Args:
            api_key: UMLS API key from https://uts.nlm.nih.gov/uts/profile
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Exponential backoff factor for retries
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Configure session with retry logic
        self.session = self._create_session()

        # Rate limiting
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 10 requests/second max

        logger.info("UMLS Client initialized")

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
        Make authenticated request to UMLS API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            requests.HTTPError: If request fails
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/{endpoint}"

        # Add API key to params
        request_params = params or {}
        request_params["apiKey"] = self.api_key

        logger.debug(f"UMLS API Request: {endpoint} with params: {request_params}")

        try:
            response = self.session.get(
                url,
                params=request_params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"UMLS API Response: {len(data.get('result', {}).get('results', []))} results")

            return data

        except requests.exceptions.Timeout as e:
            logger.error(f"UMLS API timeout: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"UMLS API HTTP error: {e}")
            if e.response.status_code == 401:
                raise ValueError("Invalid UMLS API key") from e
            elif e.response.status_code == 429:
                raise RuntimeError("UMLS API rate limit exceeded") from e
            raise
        except Exception as e:
            logger.error(f"UMLS API request failed: {e}")
            raise

    def search_concept(
        self,
        term: str,
        search_type: str = "words",
        page_size: int = 10,
        source_vocabularies: Optional[List[str]] = None
    ) -> List[UMLSConcept]:
        """
        Search for medical concepts by term.

        Args:
            term: Search term (e.g., "heart attack", "diabetes")
            search_type: Search method:
                - "words": Matches all query words (default)
                - "exact": Exact synonym match
                - "normalizedString": Removes lexical variations
                - "rightTruncation": Prefix matching
            page_size: Number of results to return (max 100)
            source_vocabularies: Filter by vocabularies (e.g., ["SNOMEDCT_US", "ICD10CM"])

        Returns:
            List of UMLS concepts matching the search term

        Example:
            >>> concepts = client.search_concept("myocardial infarction")
            >>> concepts[0].cui
            'C0027051'
            >>> concepts[0].preferred_name
            'Myocardial infarction'
        """
        if not term or not term.strip():
            return []

        params = {
            "string": term.strip(),
            "searchType": search_type,
            "pageSize": min(page_size, 100),
            "returnIdType": "concept"
        }

        if source_vocabularies:
            params["sabs"] = ",".join(source_vocabularies)

        try:
            data = self._make_request(f"search/{self.VERSION}", params)

            results = data.get("result", {}).get("results", [])

            concepts = []
            for item in results:
                concept = UMLSConcept(
                    cui=item.get("ui", ""),
                    preferred_name=item.get("name", ""),
                    source_vocabularies=[item.get("rootSource", "")],
                    confidence=1.0,  # Exact match from UMLS
                    metadata={
                        "uri": item.get("uri", ""),
                        "search_term": term,
                        "search_type": search_type
                    }
                )
                concepts.append(concept)

            logger.info(f"Found {len(concepts)} concepts for term: '{term}'")
            return concepts

        except Exception as e:
            logger.error(f"Search failed for term '{term}': {e}")
            return []

    def get_cui_details(self, cui: str) -> Optional[UMLSConcept]:
        """
        Get detailed information for a CUI.

        Args:
            cui: Concept Unique Identifier (e.g., "C0027051")

        Returns:
            Detailed UMLS concept or None if not found

        Example:
            >>> concept = client.get_cui_details("C0027051")
            >>> concept.preferred_name
            'Myocardial infarction'
            >>> concept.semantic_types
            ['Disease or Syndrome']
        """
        if not cui or not cui.startswith("C"):
            logger.warning(f"Invalid CUI format: {cui}")
            return None

        try:
            # Get basic concept info
            data = self._make_request(f"content/{self.VERSION}/CUI/{cui}")

            result = data.get("result", {})

            concept = UMLSConcept(
                cui=cui,
                preferred_name=result.get("name", ""),
                semantic_types=result.get("semanticTypes", []),
                metadata={
                    "uri": result.get("uri", ""),
                    "ui": result.get("ui", ""),
                    "classType": result.get("classType", "")
                }
            )

            # Enrich with synonyms
            synonyms = self.get_synonyms(cui)
            concept.synonyms = synonyms

            # Enrich with definitions
            definitions = self.get_definitions(cui)
            concept.definitions = definitions

            logger.info(f"Retrieved details for CUI: {cui}")
            return concept

        except Exception as e:
            logger.error(f"Failed to get CUI details for {cui}: {e}")
            return None

    def get_synonyms(self, cui: str, max_synonyms: int = 20) -> List[str]:
        """
        Get synonyms (atoms) for a CUI.

        Args:
            cui: Concept Unique Identifier
            max_synonyms: Maximum number of synonyms to return

        Returns:
            List of synonym strings
        """
        if not cui or not cui.startswith("C"):
            return []

        try:
            params = {
                "pageSize": max_synonyms
            }

            data = self._make_request(
                f"content/{self.VERSION}/CUI/{cui}/atoms",
                params
            )

            results = data.get("result", [])

            synonyms = []
            for atom in results:
                name = atom.get("name", "").strip()
                if name and name not in synonyms:
                    synonyms.append(name)

            logger.debug(f"Found {len(synonyms)} synonyms for CUI: {cui}")
            return synonyms

        except Exception as e:
            logger.error(f"Failed to get synonyms for {cui}: {e}")
            return []

    def get_definitions(self, cui: str, max_definitions: int = 5) -> List[str]:
        """
        Get definitions for a CUI.

        Args:
            cui: Concept Unique Identifier
            max_definitions: Maximum number of definitions to return

        Returns:
            List of definition strings
        """
        if not cui or not cui.startswith("C"):
            return []

        try:
            params = {
                "pageSize": max_definitions
            }

            data = self._make_request(
                f"content/{self.VERSION}/CUI/{cui}/definitions",
                params
            )

            results = data.get("result", [])

            definitions = []
            for defn in results:
                value = defn.get("value", "").strip()
                if value:
                    definitions.append(value)

            logger.debug(f"Found {len(definitions)} definitions for CUI: {cui}")
            return definitions

        except Exception as e:
            logger.error(f"Failed to get definitions for {cui}: {e}")
            return []

    def get_source_vocabularies(self, cui: str) -> List[str]:
        """
        Get all source vocabularies containing this CUI.

        Args:
            cui: Concept Unique Identifier

        Returns:
            List of vocabulary abbreviations (e.g., ['SNOMEDCT_US', 'ICD10CM'])
        """
        if not cui or not cui.startswith("C"):
            return []

        try:
            data = self._make_request(
                f"content/{self.VERSION}/CUI/{cui}/atoms"
            )

            results = data.get("result", [])

            vocabularies = set()
            for atom in results:
                root_source = atom.get("rootSource", "")
                if root_source:
                    vocabularies.add(root_source)

            vocab_list = sorted(list(vocabularies))
            logger.debug(f"Found {len(vocab_list)} vocabularies for CUI: {cui}")
            return vocab_list

        except Exception as e:
            logger.error(f"Failed to get vocabularies for {cui}: {e}")
            return []

    def validate_api_key(self) -> bool:
        """
        Validate that the API key is valid and active.

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            # Try a simple search to validate
            self.search_concept("diabetes", page_size=1)
            logger.info("UMLS API key validated successfully")
            return True
        except ValueError as e:
            if "Invalid UMLS API key" in str(e):
                logger.error("UMLS API key validation failed")
                return False
            raise
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False


__all__ = ["UMLSClient", "UMLSConcept"]
