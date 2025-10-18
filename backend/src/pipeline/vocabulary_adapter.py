"""
Vocabulary Adapter: OHDSIClient interface for LocalVocabulary

Provides OHDSIClient-compatible interface using LocalVocabulary,
allowing seamless integration with existing pipeline code.
"""

from typing import List, Optional
from .local_vocabulary import get_vocabulary, LocalVocabulary
from .clients import OMOPConcept
import logging

logger = logging.getLogger(__name__)


class VocabularyAdapter:
    """
    Adapter that provides OHDSIClient-compatible interface using LocalVocabulary.

    This allows existing code using OHDSIClient to work with LocalVocabulary
    without modification.

    Usage:
        # Instead of:
        # from .clients import OHDSIClient
        # client = OHDSIClient()

        # Use:
        from .vocabulary_adapter import VocabularyAdapter
        client = VocabularyAdapter()
    """

    def __init__(self, vocab_dir: str = "vocabulary"):
        """
        Initialize adapter with LocalVocabulary.

        Args:
            vocab_dir: Path to vocabulary CSV files
        """
        self.vocab: LocalVocabulary = get_vocabulary(vocab_dir)
        logger.info(f"VocabularyAdapter initialized with local vocabulary from {vocab_dir}")

    def search_standard_concepts(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 100
    ) -> List[OMOPConcept]:
        """
        Search for standard concepts (OHDSIClient compatible).

        Args:
            query: Search term
            domain: Optional domain filter (Drug, Condition, etc.)
            limit: Maximum number of results

        Returns:
            List of OMOPConcept objects
        """
        try:
            # Use search_and_map for automatic standard concept mapping
            results = self.vocab.search_and_map(query, domain=domain, limit=limit)

            # Convert to OMOPConcept objects
            concepts = []
            for concept_dict in results:
                omop_concept = OMOPConcept(
                    concept_id=concept_dict["concept_id"],
                    concept_name=concept_dict["concept_name"],
                    domain_id=concept_dict["domain_id"],
                    vocabulary_id=concept_dict["vocabulary_id"],
                    concept_class_id=concept_dict["concept_class_id"],
                    standard_concept=concept_dict.get("standard_concept", "S"),
                    concept_code=concept_dict["concept_code"]
                )
                concepts.append(omop_concept)

            return concepts

        except Exception as e:
            logger.error(f"Error searching concepts for '{query}': {e}")
            return []

    def get_concept_by_id(self, concept_id: int) -> Optional[OMOPConcept]:
        """
        Get concept by ID (OHDSIClient compatible).

        Args:
            concept_id: OMOP concept ID

        Returns:
            OMOPConcept object or None
        """
        try:
            concept_dict = self.vocab.get_concept_by_id(concept_id)

            if not concept_dict:
                return None

            return OMOPConcept(
                concept_id=concept_dict["concept_id"],
                concept_name=concept_dict["concept_name"],
                domain_id=concept_dict["domain_id"],
                vocabulary_id=concept_dict["vocabulary_id"],
                concept_class_id=concept_dict["concept_class_id"],
                standard_concept=concept_dict.get("standard_concept", ""),
                concept_code=concept_dict["concept_code"]
            )

        except Exception as e:
            logger.error(f"Error getting concept {concept_id}: {e}")
            return None

    def get_concept_ancestors(
        self,
        concept_id: int,
        max_levels: Optional[int] = None
    ) -> List[OMOPConcept]:
        """
        Get ancestor concepts (OHDSIClient compatible).

        Args:
            concept_id: OMOP concept ID
            max_levels: Maximum hierarchy levels

        Returns:
            List of ancestor OMOPConcept objects
        """
        try:
            ancestors_df = self.vocab.get_concept_ancestors(concept_id, max_levels)

            concepts = []
            for _, row in ancestors_df.iterrows():
                omop_concept = OMOPConcept(
                    concept_id=row["concept_id"],
                    concept_name=row["concept_name"],
                    domain_id=row["domain_id"],
                    vocabulary_id=row["vocabulary_id"],
                    concept_class_id=row["concept_class_id"],
                    standard_concept=row.get("standard_concept", "S"),
                    concept_code=row["concept_code"]
                )
                concepts.append(omop_concept)

            return concepts

        except Exception as e:
            logger.error(f"Error getting ancestors for {concept_id}: {e}")
            return []

    def map_source_to_standard(
        self,
        source_concept_id: int,
        relationship_id: str = "Maps to"
    ) -> List[OMOPConcept]:
        """
        Map source concept to standard concepts (OHDSIClient compatible).

        Args:
            source_concept_id: Source concept ID
            relationship_id: Relationship type (default: "Maps to")

        Returns:
            List of standard OMOPConcept objects
        """
        try:
            mappings_df = self.vocab.get_concept_mappings(
                source_concept_id,
                relationship_id
            )

            concepts = []
            for _, row in mappings_df.iterrows():
                omop_concept = OMOPConcept(
                    concept_id=row["concept_id"],
                    concept_name=row["concept_name"],
                    domain_id=row["domain_id"],
                    vocabulary_id=row["vocabulary_id"],
                    concept_class_id=row["concept_class_id"],
                    standard_concept=row.get("standard_concept", "S"),
                    concept_code=row["concept_code"]
                )
                concepts.append(omop_concept)

            return concepts

        except Exception as e:
            logger.error(f"Error mapping concept {source_concept_id}: {e}")
            return []

    def search_concept(
        self,
        term: str,
        vocabulary: Optional[str] = None,
        domain: Optional[str] = None,
        page_size: int = 10,
        standard_only: bool = False
    ) -> List[OMOPConcept]:
        """
        Search for concepts (CDMMapper compatible method).

        Matches OHDSIClient.search_concept() signature exactly.

        Args:
            term: Search term
            vocabulary: Optional vocabulary filter (e.g., "SNOMED", "RxNorm")
            domain: Optional domain filter
            page_size: Maximum number of results
            standard_only: Return only standard concepts

        Returns:
            List of OMOPConcept objects
        """
        try:
            # Use LocalVocabulary search_concepts
            results_df = self.vocab.search_concepts(
                query=term,
                domain=domain,
                vocabulary=vocabulary,
                standard_only=standard_only,
                limit=page_size
            )

            # Convert DataFrame to OMOPConcept objects
            concepts = []
            for _, row in results_df.iterrows():
                omop_concept = OMOPConcept(
                    concept_id=row["concept_id"],
                    concept_name=row["concept_name"],
                    domain_id=row["domain_id"],
                    vocabulary_id=row["vocabulary_id"],
                    concept_class_id=row["concept_class_id"],
                    standard_concept=row.get("standard_concept", ""),
                    concept_code=row["concept_code"]
                )
                concepts.append(omop_concept)

            return concepts

        except Exception as e:
            logger.error(f"Error searching concepts for '{query}': {e}")
            return []


# Convenience function for easy migration
def get_vocabulary_adapter(vocab_dir: str = "vocabulary") -> VocabularyAdapter:
    """
    Get VocabularyAdapter instance (singleton pattern).

    Usage:
        from .vocabulary_adapter import get_vocabulary_adapter

        client = get_vocabulary_adapter()
        results = client.search_standard_concepts("diabetes")
    """
    return VocabularyAdapter(vocab_dir)
