"""
Prompt templates for Stage 1: Structured Extraction.

Guides LLM to extract clinical trial criteria into structured JSON format
with edge case handling (negation, temporal, assumptions).
"""

SYSTEM_PROMPT = """You are a medical NLP expert specializing in clinical trial eligibility criteria extraction.

Your task is to parse raw clinical trial inclusion/exclusion criteria text into structured JSON format.

CRITICAL REQUIREMENTS:
1. Preserve original text verbatim in the "text" field
2. Generate unique IDs (inc_001, inc_002, exc_001, etc.)
3. Extract operator and value separately
4. Detect negations (NOT, exclude, no history of)
5. Identify temporal constraints (within X hours/days/months, before, after)
6. Track assumptions made during extraction
7. Handle complex criteria with sub_criteria (AND/OR logic)

ENTITY TYPES:
- demographic: Age, gender, race, etc.
- condition: Diseases, diagnoses, medical conditions
- procedure: Surgeries, interventions, treatments
- measurement: Lab values, vital signs, scores
- medication: Drugs, therapies, drug classes

OPERATORS:
- Use: >, <, >=, <=, ==, !=, IN, NOT IN, LIKE
- Be precise about >= vs > based on original text

EDGE CASES TO HANDLE:
1. Negation: "NOT diabetic", "exclude pregnancy", "no history of"
   -> Set negation: true
2. Temporal: "within 24 hours", "before admission", "after 6 months"
   -> Extract to temporal_constraint
3. Value assumptions: "adult" -> assume age >= 18
   -> Add to assumptions_made: ["Assumed 'adult' means age >= 18"]
4. Complex criteria: "MAP e65 AND Lactate >2"
   -> Use sub_criteria array
5. Irrelevant text: "Participants will be contacted"
   -> Return empty arrays (not an error)

EXAMPLES:
Input: "Adult patients aged 18 years or older"
Output:
{
  "id": "inc_001",
  "text": "Adult patients aged 18 years or older",
  "entity_type": "demographic",
  "attribute": "age",
  "operator": ">=",
  "value": "18",
  "unit": "years",
  "negation": false,
  "assumptions_made": []
}

Input: "NOT pregnant"
Output:
{
  "id": "exc_001",
  "text": "NOT pregnant",
  "entity_type": "condition",
  "attribute": "pregnancy",
  "negation": true
}

Input: "Lactate >2 mmol/L within 24 hours of ICU admission"
Output:
{
  "id": "inc_002",
  "text": "Lactate >2 mmol/L within 24 hours of ICU admission",
  "entity_type": "measurement",
  "attribute": "lactate",
  "operator": ">",
  "value": "2",
  "unit": "mmol/L",
  "temporal_constraint": {
    "operator": "within_last",
    "value": 24,
    "unit": "hours",
    "reference_point": "icu_admission"
  }
}

Input: "Septic shock (MAP e65 AND Lactate >2)"
Output:
{
  "id": "inc_003",
  "text": "Septic shock (MAP e65 AND Lactate >2)",
  "entity_type": "condition",
  "attribute": "septic_shock",
  "sub_criteria": [
    {
      "id": "inc_003_a",
      "text": "MAP e65",
      "entity_type": "measurement",
      "attribute": "mean_arterial_pressure",
      "operator": ">=",
      "value": "65",
      "unit": "mmHg"
    },
    {
      "id": "inc_003_b",
      "text": "Lactate >2",
      "entity_type": "measurement",
      "attribute": "lactate",
      "operator": ">",
      "value": "2",
      "unit": "mmol/L"
    }
  ]
}
"""


def build_extraction_prompt(raw_criteria: str) -> str:
    """
    Build the extraction prompt for a given raw criteria text.

    Args:
        raw_criteria: Raw inclusion/exclusion criteria text

    Returns:
        Formatted prompt string
    """
    return f"""Extract clinical trial inclusion and exclusion criteria into structured JSON format.

INPUT CRITERIA:
{raw_criteria}

INSTRUCTIONS:
1. Read the criteria carefully
2. Separate inclusion and exclusion criteria
3. Extract each criterion as a CriterionEntity
4. Detect negations, temporal constraints, and value assumptions
5. Handle complex criteria with sub_criteria
6. If text contains no extractable criteria, return empty arrays

OUTPUT FORMAT:
Return a JSON object with this structure:
{{
  "inclusion": [
    {{
      "id": "inc_001",
      "text": "original criterion text",
      "entity_type": "demographic|condition|procedure|measurement|medication",
      "attribute": "age|diagnosis|lab_value|etc",
      "operator": ">|<|>=|<=|==|!=|IN|NOT IN|LIKE|null",
      "value": "numeric or text value",
      "unit": "years|mmHg|mmol/L|etc",
      "negation": false,
      "temporal_constraint": null,
      "sub_criteria": null,
      "assumptions_made": []
    }}
  ],
  "exclusion": [...]
}}

Now extract the criteria from the input above.
"""


CORRECTIVE_RETRY_PROMPT = """Your previous extraction attempt had validation errors:

{validation_error}

Please correct the JSON structure and provide a valid response that follows the schema requirements.

Common issues to check:
- All required fields present (id, text, entity_type, attribute)
- entity_type must be one of: demographic, condition, procedure, measurement, medication
- operator must be one of: >, <, >=, <=, ==, !=, IN, NOT IN, LIKE (or null)
- temporal_constraint.value must be > 0
- temporal_constraint.unit must be one of: hours, days, months, years

Original criteria:
{raw_criteria}

Provide the corrected extraction:
"""
