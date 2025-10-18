"""
API clients for medical terminology services.

This module provides clients for:
- UMLS (Unified Medical Language System)
- OHDSI Athena (OMOP CDM vocabularies)
"""

from .umls_client import UMLSClient, UMLSConcept
from .ohdsi_client import OHDSIClient, OMOPConcept, ConceptRelationship
from .cache_manager import CacheManager

__all__ = [
    "UMLSClient",
    "UMLSConcept",
    "OHDSIClient",
    "OMOPConcept",
    "ConceptRelationship",
    "CacheManager",
]
