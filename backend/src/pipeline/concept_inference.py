"""
Concept inference module for omitted clinical concepts.

Infers missing concepts from contextual clues in clinical criteria according
to Trialist paper specifications (e.g., "age" from "< 18 years", "female" from "pregnant").
"""

from __future__ import annotations
import re
from typing import List, Sequence
from dataclasses import replace

from .trialist_models import EnhancedNamedEntity


# Gender-specific condition patterns
FEMALE_CONDITIONS = [
    "pregnan",  # pregnant, pregnancy, pregnancies
    "maternal",
    "cervical",
    "ovarian",
    "uterine",
    "menstrual",
    "menopause",
    "breast cancer",  # Note: mostly female but can be male
]

MALE_CONDITIONS = [
    "prostat",  # prostate, prostatic
    "testicular",
    "erectile",
    "penile",
]

# Measurement unit patterns
MEASUREMENT_UNITS = {
    "mmHg": "blood pressure",
    "mm[Hg]": "blood pressure",
    "mg/dL": "blood glucose",  # Common but not always
    "%": None,  # Too generic
    "kg/m2": "body mass index",
}


def infer_age_concept(entities: Sequence[EnhancedNamedEntity]) -> List[EnhancedNamedEntity]:
    """
    Infer age concept from standalone age values without explicit "age" text.

    Args:
        entities: List of entities to analyze

    Returns:
        List of inferred age concept entities
    """
    inferred: List[EnhancedNamedEntity] = []

    for entity in entities:
        # Check if entity has age-related value without "age" text
        if _is_age_value_without_explicit_age(entity):
            # Create inferred age concept
            age_entity = EnhancedNamedEntity(
                text="age",
                type="concept",
                domain="Demographic",
                is_inferred=True,
                inferred_from=entity.text
            )
            inferred.append(age_entity)

    return inferred


def _is_age_value_without_explicit_age(entity: EnhancedNamedEntity) -> bool:
    """
    Check if entity is an age value without explicit "age" text.

    Args:
        entity: Entity to check

    Returns:
        True if entity is age value without "age" text
    """
    # Must have time unit (years, months, etc.)
    if not entity.unit or entity.unit not in ["years", "year", "months", "month", "days", "day"]:
        return False

    # Must have numeric value or range
    if entity.numeric_value is None and entity.value_range is None:
        return False

    # Must NOT already contain "age" in text
    text_lower = entity.text.lower()
    if "age" in text_lower:
        return False

    # Most likely age if domain is Value or Demographic with time unit + number
    return entity.domain in ["Value", "Demographic", "Quantity"]


def infer_gender_from_condition(entities: Sequence[EnhancedNamedEntity]) -> List[EnhancedNamedEntity]:
    """
    Infer gender from gender-specific conditions (pregnant, prostate cancer).

    Args:
        entities: List of entities to analyze

    Returns:
        List of inferred gender entities
    """
    inferred: List[EnhancedNamedEntity] = []

    for entity in entities:
        # Check for female-specific conditions
        gender = _detect_gender_from_condition(entity.text)
        if gender:
            gender_entity = EnhancedNamedEntity(
                text=gender,
                type="concept",
                domain="Demographic",
                is_inferred=True,
                inferred_from=entity.text
            )
            inferred.append(gender_entity)

    return inferred


def _detect_gender_from_condition(text: str) -> str | None:
    """
    Detect gender from condition text.

    Args:
        text: Condition text to analyze

    Returns:
        "male" or "female" if detected, None otherwise
    """
    text_lower = text.lower()

    # Check for female-specific conditions
    for pattern in FEMALE_CONDITIONS:
        if pattern in text_lower:
            return "female"

    # Check for male-specific conditions
    for pattern in MALE_CONDITIONS:
        if pattern in text_lower:
            return "male"

    return None


def infer_measurement_concept(entities: Sequence[EnhancedNamedEntity]) -> List[EnhancedNamedEntity]:
    """
    Infer measurement concept from standalone measurement values.

    Args:
        entities: List of entities to analyze

    Returns:
        List of inferred measurement concept entities
    """
    inferred: List[EnhancedNamedEntity] = []

    for entity in entities:
        # Check if entity is standalone measurement value
        measurement_name = _infer_measurement_from_unit(entity)
        if measurement_name:
            measurement_entity = EnhancedNamedEntity(
                text=measurement_name,
                type="concept",
                domain="Measurement",
                is_inferred=True,
                inferred_from=entity.text
            )
            inferred.append(measurement_entity)

    return inferred


def _infer_measurement_from_unit(entity: EnhancedNamedEntity) -> str | None:
    """
    Infer measurement concept from unit.

    Args:
        entity: Entity to analyze

    Returns:
        Measurement name if inferred, None otherwise
    """
    # Must have numeric value
    if entity.numeric_value is None and entity.value_range is None:
        return None

    # Must have unit
    if not entity.unit and not entity.ucum_unit:
        return None

    # Must NOT already be a Measurement domain
    if entity.domain == "Measurement":
        return None

    # Must be Value domain with standalone numeric + unit
    if entity.domain != "Value":
        return None

    # Check unit patterns
    unit = entity.ucum_unit or entity.unit
    if unit in MEASUREMENT_UNITS:
        return MEASUREMENT_UNITS[unit]

    # Check text for measurement name
    text_lower = entity.text.lower()
    # If text only contains operator + number + unit, it's a standalone value
    # Pattern: "< 140 mmHg" or ">= 7.0%" etc.
    if re.match(r'^[<>=]+\s*\d+\.?\d*\s*\w+$', entity.text.strip()):
        # Infer based on unit
        if unit in MEASUREMENT_UNITS:
            return MEASUREMENT_UNITS[unit]

    return None


def infer_omitted_concepts(entities: Sequence[EnhancedNamedEntity]) -> List[EnhancedNamedEntity]:
    """
    Infer all omitted concepts from entity list.

    Args:
        entities: List of entities to analyze

    Returns:
        Combined list of original + inferred entities
    """
    # Start with original entities
    result = list(entities)

    # Infer age concepts
    age_inferred = infer_age_concept(entities)
    result.extend(age_inferred)

    # Infer gender from conditions
    gender_inferred = infer_gender_from_condition(entities)
    result.extend(gender_inferred)

    # Infer measurement concepts
    measurement_inferred = infer_measurement_concept(entities)
    result.extend(measurement_inferred)

    return result


__all__ = [
    "infer_age_concept",
    "infer_gender_from_condition",
    "infer_measurement_concept",
    "infer_omitted_concepts"
]
