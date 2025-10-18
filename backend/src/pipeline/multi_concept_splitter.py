"""
Multi-concept splitting module for compound clinical concepts.

Splits compound concepts connected by logical operators (AND, OR) into
separate entities with relationship tracking according to Trialist paper.
"""

from __future__ import annotations
import re
import uuid
from typing import List, Optional, Sequence
from dataclasses import replace

from .trialist_models import EnhancedNamedEntity


def _detect_logical_operator(text: str) -> Optional[str]:
    """
    Detect logical operator (AND/OR) in text.

    Priority: AND > OR > comma-or

    Args:
        text: Text to analyze

    Returns:
        "AND" or "OR" if found, None otherwise
    """
    text_upper = text.upper()

    # Check for explicit AND operator (case-insensitive)
    if re.search(r'\bAND\b', text_upper):
        return "AND"

    # Check for explicit OR operator (case-insensitive)
    if re.search(r'\bOR\b', text_upper):
        return "OR"

    # Check for comma-separated list (implies OR)
    # Look for pattern: "A, B, or C" or "A, B, and C"
    if ',' in text:
        # If contains comma AND 'or', it's an OR list
        if re.search(r',\s*or\b', text.lower()):
            return "OR"
        # If contains comma AND 'and', it's an AND list
        if re.search(r',\s*and\b', text.lower()):
            return "AND"

    return None


def split_multi_concepts(text: str, base_entity: EnhancedNamedEntity) -> List[EnhancedNamedEntity]:
    """
    Split compound concepts connected by logical operators into separate entities.

    Args:
        text: Text containing potential compound concepts
        base_entity: Base entity to use as template for split entities

    Returns:
        List of split entities with relationship tracking
    """
    # Detect logical operator
    operator = _detect_logical_operator(text)

    # No operator found - return single entity
    if operator is None:
        return [base_entity]

    # Split text based on operator
    parts = _split_text_by_operator(text, operator)

    # No valid splits - return single entity
    if len(parts) <= 1:
        return [base_entity]

    # Generate group ID for related entities
    group_id = str(uuid.uuid4())[:8]

    # Create entities for each part
    entities: List[EnhancedNamedEntity] = []
    entity_ids: List[str] = []

    for part in parts:
        entity_id = str(uuid.uuid4())[:8]
        entity_ids.append(entity_id)

        # Create new entity based on base entity
        metadata = dict(base_entity.metadata) if base_entity.metadata else {}
        metadata["group_id"] = group_id
        metadata["entity_id"] = entity_id

        entity = replace(
            base_entity,
            text=part.strip(),
            logical_operator=operator,
            metadata=metadata
        )
        entities.append(entity)

    # Populate related_entity_ids for each entity (excluding itself)
    final_entities: List[EnhancedNamedEntity] = []
    for i, entity in enumerate(entities):
        related_ids = [eid for j, eid in enumerate(entity_ids) if j != i]
        entity = replace(entity, related_entity_ids=related_ids)
        final_entities.append(entity)

    return final_entities


def _split_text_by_operator(text: str, operator: str) -> List[str]:
    """
    Split text by logical operator.

    Args:
        text: Text to split
        operator: "AND" or "OR"

    Returns:
        List of split text parts
    """
    if operator == "AND":
        # Split by AND (case-insensitive)
        parts = re.split(r'\s+and\s+', text, flags=re.IGNORECASE)
        return [part.strip() for part in parts if part.strip()]

    elif operator == "OR":
        # First try to split by comma + or pattern (for lists)
        if re.search(r',\s*or\b', text.lower()):
            # Split by comma, then handle final 'or'
            parts = re.split(r',\s*', text)
            # Remove 'or' from last part if present
            if parts:
                parts[-1] = re.sub(r'^\s*or\s+', '', parts[-1], flags=re.IGNORECASE)
            return [part.strip() for part in parts if part.strip()]
        else:
            # Split by OR (case-insensitive)
            parts = re.split(r'\s+or\s+', text, flags=re.IGNORECASE)
            return [part.strip() for part in parts if part.strip()]

    return [text]


__all__ = [
    "split_multi_concepts",
    "_detect_logical_operator",
    "_split_text_by_operator"
]
