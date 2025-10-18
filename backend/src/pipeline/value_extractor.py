"""
Value extraction module for clinical trial criteria.

Extracts operators, numeric values, units, and performs UCUM unit standardization
according to Trialist paper specifications.
"""

from __future__ import annotations
import re
from typing import TypedDict


# UCUM unit mappings for standardization
UCUM_UNIT_MAPPINGS: dict[str, str] = {
    # Time units
    "years": "a",
    "year": "a",
    "yr": "a",
    "y": "a",
    "months": "mo",
    "month": "mo",
    "mon": "mo",
    "weeks": "wk",
    "week": "wk",
    "wk": "wk",
    "days": "d",
    "day": "d",
    "hours": "h",
    "hour": "h",
    "hr": "h",
    "h": "h",
    "minutes": "min",
    "minute": "min",
    "min": "min",

    # Measurement units
    "mmHg": "mm[Hg]",
    "%": "%",
    "percent": "%",
    "mg/dL": "mg/dL",
    "mg/dl": "mg/dL",
    "kg": "kg",
    "kg/m2": "kg/m2",
    "kg/m^2": "kg/m2",
    "g": "g",
    "mg": "mg",
    "mL": "mL",
    "ml": "mL",
    "L": "L",
    "cm": "cm",
    "m": "m",
}


class NumericResult(TypedDict):
    """Result type for numeric value extraction."""
    numeric_value: float | None
    value_range: tuple[float, float] | None


class UnitResult(TypedDict):
    """Result type for unit extraction."""
    unit: str | None
    ucum_unit: str | None


class ValueComponents(TypedDict):
    """Complete value extraction result."""
    operator: str | None
    numeric_value: float | None
    value_range: tuple[float, float] | None
    unit: str | None
    ucum_unit: str | None


def extract_operator(text: str) -> str | None:
    """
    Extract comparison operator from text.

    Detects: <, >, ≥, ≤, =, between

    Args:
        text: Input text containing potential operator

    Returns:
        Operator string or None if not found

    Examples:
        >>> extract_operator("age >= 18 years")
        '>='
        >>> extract_operator("BMI between 18.5 and 24.9")
        'between'
    """
    text = text.lower()

    # Check for 'between' first (multi-character operator)
    if re.search(r'\bbetween\b', text):
        return "between"

    # Check for comparison operators
    # Match >= or ≥
    if re.search(r'>=|≥', text):
        return ">="

    # Match <= or ≤
    if re.search(r'<=|≤', text):
        return "<="

    # Match > (but not part of >= or ≥)
    if re.search(r'(?<!>)>(?!=)', text):
        return ">"

    # Match < (but not part of <= or ≤)
    if re.search(r'(?<!<)<(?!=)', text):
        return "<"

    # Match = (but not part of >= or <=)
    if re.search(r'(?<![><])=(?!=)', text):
        return "="

    return None


def extract_numeric_value(text: str) -> NumericResult:
    """
    Extract numeric value or range from text.

    Handles:
    - Single values: "age >= 18"
    - Ranges with 'and': "between 18.5 and 24.9"
    - Ranges with dash: "18-65"
    - Ranges with 'to': "50 to 100"

    Args:
        text: Input text containing potential numeric values

    Returns:
        Dictionary with numeric_value (single) or value_range (tuple)

    Examples:
        >>> extract_numeric_value("age >= 18 years")
        {'numeric_value': 18.0, 'value_range': None}
        >>> extract_numeric_value("BMI between 18.5 and 24.9")
        {'numeric_value': None, 'value_range': (18.5, 24.9)}
    """
    # Pattern to match floating point or integer numbers
    # More specific: require operator or range context
    number_pattern = r'(\d+(?:\.\d+)?)'

    # Try to find range patterns first
    # Pattern: "X and Y" or "X-Y" or "X to Y"
    range_patterns = [
        rf'{number_pattern}\s+and\s+{number_pattern}',
        rf'{number_pattern}\s*-\s*{number_pattern}(?:\s|$)',  # Dash with word boundary
        rf'{number_pattern}\s+to\s+{number_pattern}'
    ]

    for pattern in range_patterns:
        match = re.search(pattern, text)
        if match:
            lower = float(match.group(1))
            upper = float(match.group(2))
            return {"numeric_value": None, "value_range": (lower, upper)}

    # Try to find single value near an operator
    # Look for patterns like: ">= 18", "< 126", "> 7.5"
    operator_value_pattern = rf'[><=≥≤]\s*{number_pattern}'
    match = re.search(operator_value_pattern, text)
    if match:
        value = float(match.group(1))
        return {"numeric_value": value, "value_range": None}

    return {"numeric_value": None, "value_range": None}


def extract_unit(text: str) -> UnitResult:
    """
    Extract unit and map to UCUM standard.

    Extracts common clinical units and converts to UCUM format.

    Args:
        text: Input text containing potential unit

    Returns:
        Dictionary with original unit and UCUM-standardized unit

    Examples:
        >>> extract_unit("age >= 18 years")
        {'unit': 'years', 'ucum_unit': 'a'}
        >>> extract_unit("BP <= 140 mmHg")
        {'unit': 'mmHg', 'ucum_unit': 'mm[Hg]'}
    """
    # Special handling for % which doesn't have word boundaries
    if '%' in text:
        return {"unit": "%", "ucum_unit": "%"}

    # Build pattern from known units (longest first to match "kg/m2" before "kg")
    # Exclude % since it's handled above
    sorted_units = sorted(
        [u for u in UCUM_UNIT_MAPPINGS.keys() if u != '%' and u != 'percent'],
        key=len,
        reverse=True
    )
    unit_pattern = '|'.join(re.escape(u) for u in sorted_units)

    # Match units (case-insensitive for some, case-sensitive for abbreviations)
    match = re.search(rf'\b({unit_pattern})\b', text, re.IGNORECASE)

    if match:
        unit = match.group(1)

        # Try exact match first, then case-insensitive
        if unit in UCUM_UNIT_MAPPINGS:
            ucum_unit = UCUM_UNIT_MAPPINGS[unit]
        else:
            # Case-insensitive lookup
            unit_lower = unit.lower()
            ucum_unit = UCUM_UNIT_MAPPINGS.get(unit_lower)
            if ucum_unit:
                unit = unit_lower  # Normalize to lowercase version

        return {"unit": unit, "ucum_unit": ucum_unit}

    return {"unit": None, "ucum_unit": None}


def extract_value_components(text: str) -> ValueComponents:
    """
    Extract all value components from text.

    Combines operator, numeric value, and unit extraction.

    Args:
        text: Input text to extract values from

    Returns:
        Complete dictionary with all value components

    Examples:
        >>> extract_value_components("HbA1c > 7.0%")
        {
            'operator': '>',
            'numeric_value': 7.0,
            'value_range': None,
            'unit': '%',
            'ucum_unit': '%'
        }
    """
    operator = extract_operator(text)
    numeric_result = extract_numeric_value(text)
    unit_result = extract_unit(text)

    return {
        "operator": operator,
        "numeric_value": numeric_result["numeric_value"],
        "value_range": numeric_result["value_range"],
        "unit": unit_result["unit"],
        "ucum_unit": unit_result["ucum_unit"]
    }


__all__ = [
    "extract_operator",
    "extract_numeric_value",
    "extract_unit",
    "extract_value_components",
    "UCUM_UNIT_MAPPINGS",
    "NumericResult",
    "UnitResult",
    "ValueComponents"
]
