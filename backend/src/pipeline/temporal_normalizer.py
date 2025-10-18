"""
Temporal normalization module for clinical trial criteria.

Converts temporal expressions to ISO 8601 duration format and extracts
reference points according to Trialist paper specifications.
"""

from __future__ import annotations
import re
from typing import TypedDict


# Temporal pattern types (from Trialist paper)
TEMPORAL_PATTERNS = {
    "XBeforeY": "X occurs before Y",
    "XBeforeYwithTime": "X before Y with time interval",
    "XAfterY": "X occurs after Y",
    "XAfterYwithTime": "X after Y with time interval",
    "XDuringY": "X occurs during Y",
    "XAtY": "X occurs at Y",
    "XWithinTime": "X within time period",
    "XForDuration": "X for duration",
    "XEveryInterval": "X every interval"
}


# Reference point patterns (order matters - more specific patterns first)
REFERENCE_POINTS = {
    # Treatment-related (most specific first)
    "chemotherapy": ["chemotherapy start", "chemotherapy initiation", "chemotherapy", "chemo start"],
    "radiation": ["radiation start", "radiation therapy start", "radiation therapy", "radiotherapy"],
    "treatment": ["treatment start", "treatment initiation", "treatment"],

    # Enrollment and study-related
    "enrollment": ["enrollment", "enroll", "enrolled", "randomization", "randomized"],
    "screening": ["screening", "screen"],
    "baseline": ["baseline", "initial"],

    # Hospital events
    "admission": ["admission", "admit", "admitted", "hospitalization", "hospitalized"],
    "discharge": ["discharge", "discharged"],

    # Surgical events (most specific first)
    "post-operative": ["post-operative", "post-surgery", "postoperative"],
    "pre-operative": ["pre-operative", "pre-surgery", "preoperative"],
    "surgery": ["surgery", "surgical", "operation", "operative"],

    # Medical procedures
    "procedure": ["procedure", "procedural"],

    # Clinical events
    "diagnosis": ["diagnosis", "diagnosed"],
    "follow-up": ["follow-up", "followup", "follow up visit"],

    # Time-based references
    "visit": ["study visit", "clinic visit", "visit"],
    "assessment": ["assessment", "evaluation"],
}


class TemporalComponents(TypedDict):
    """Result type for temporal component extraction."""
    temporal_pattern: str | None
    iso_duration: str | None
    reference_point: str | None


def normalize_temporal_duration(text: str) -> str | None:
    """
    Normalize temporal duration to ISO 8601 format.

    Converts natural language durations (e.g., "3 months", "24 hours") to
    ISO 8601 duration format (e.g., "P3M", "PT24H").

    Format: P[n]Y[n]M[n]W[n]D T[n]H[n]M[n]S
    - P prefix for period
    - T separator for time components (hours, minutes, seconds)

    Args:
        text: Input text containing temporal duration

    Returns:
        ISO 8601 duration string or None if no duration found

    Examples:
        >>> normalize_temporal_duration("3 months")
        'P3M'
        >>> normalize_temporal_duration("24 hours")
        'PT24H'
    """
    text = text.lower()

    # Patterns for different time units
    duration_patterns = [
        (r'(\d+)\s*(?:years?|yr)', 'Y', False),
        (r'(\d+)\s*(?:months?|mon)', 'M', False),
        (r'(\d+)\s*(?:weeks?|wk)', 'W', False),
        (r'(\d+)\s*(?:days?|d\b)', 'D', False),
        (r'(\d+)\s*(?:hours?|hr|h\b)', 'H', True),
        (r'(\d+)\s*(?:minutes?|min)', 'M', True),
    ]

    # Extract all matching durations
    period_parts = []
    time_parts = []

    for pattern, unit, is_time in duration_patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1)
            if is_time:
                time_parts.append(f"{value}{unit}")
            else:
                period_parts.append(f"{value}{unit}")

    # Build ISO 8601 string
    if period_parts or time_parts:
        iso_string = "P"
        iso_string += "".join(period_parts)

        if time_parts:
            iso_string += "T" + "".join(time_parts)

        return iso_string

    return None


def extract_reference_point(text: str) -> str | None:
    """
    Extract temporal reference point from text.

    Identifies reference events like enrollment, admission, discharge, baseline,
    surgery, procedure, diagnosis, or treatment.

    Args:
        text: Input text containing potential reference point

    Returns:
        Reference point identifier or None if not found

    Examples:
        >>> extract_reference_point("within 3 months before enrollment")
        'enrollment'
        >>> extract_reference_point("24 hours after admission")
        'admission'
    """
    text = text.lower()

    # Check each reference point category
    # Sort patterns by length (longest first) to match "treatment start" before "start"
    for ref_point, patterns in REFERENCE_POINTS.items():
        sorted_patterns = sorted(patterns, key=len, reverse=True)
        for pattern in sorted_patterns:
            if re.search(rf'\b{re.escape(pattern)}\b', text):
                return ref_point

    return None


def extract_temporal_components(text: str) -> TemporalComponents:
    """
    Extract complete temporal components from text.

    Identifies temporal pattern type, normalizes duration to ISO 8601,
    and extracts reference point.

    Args:
        text: Input text to extract temporal components from

    Returns:
        Dictionary with temporal_pattern, iso_duration, and reference_point

    Examples:
        >>> extract_temporal_components("within 3 months before enrollment")
        {
            'temporal_pattern': 'XWithinTime',
            'iso_duration': 'P3M',
            'reference_point': 'enrollment'
        }
    """
    text_lower = text.lower()

    # Extract base components
    iso_duration = normalize_temporal_duration(text)
    reference_point = extract_reference_point(text)

    # Special case: "X for duration" pattern - reference_point should be None
    # because the subject is the action, not a reference event
    if re.search(r'\bfor\b.*\b(?:months?|weeks?|days?|hours?)', text_lower):
        reference_point = None

    # Determine temporal pattern
    temporal_pattern = _determine_temporal_pattern(text_lower, iso_duration, reference_point)

    return {
        "temporal_pattern": temporal_pattern,
        "iso_duration": iso_duration,
        "reference_point": reference_point
    }


def _determine_temporal_pattern(
    text: str,
    iso_duration: str | None,
    reference_point: str | None
) -> str | None:
    """
    Determine the temporal pattern type from text and extracted components.

    Args:
        text: Lowercase input text
        iso_duration: Extracted ISO duration (if any)
        reference_point: Extracted reference point (if any)

    Returns:
        Temporal pattern identifier or None
    """
    # Check for specific pattern keywords (order matters)
    if re.search(r'\bwithin\b', text):
        return "XWithinTime"

    if re.search(r'\bevery\b', text):
        return "XEveryInterval"

    # Check for patterns with reference points first
    if reference_point:
        if re.search(r'\bat\b', text):
            return "XAtY"

        if re.search(r'\bduring\b', text):
            return "XDuringY"

        if re.search(r'\bbefore\b', text):
            if iso_duration:
                return "XBeforeYwithTime"
            return "XBeforeY"

        if re.search(r'\bafter\b', text):
            if iso_duration:
                return "XAfterYwithTime"
            return "XAfterY"

    # Check for "for" pattern (but only if no reference point detected)
    if re.search(r'\bfor\b.*\b(?:months?|weeks?|days?|hours?)', text):
        return "XForDuration"

    # If has duration but no specific pattern, default to XForDuration
    if iso_duration and not reference_point:
        return "XForDuration"

    return None


__all__ = [
    "normalize_temporal_duration",
    "extract_reference_point",
    "extract_temporal_components",
    "TEMPORAL_PATTERNS",
    "REFERENCE_POINTS",
    "TemporalComponents"
]
