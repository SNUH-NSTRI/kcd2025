"""
EligibilityExtractor: LLM-based extraction of structured eligibility criteria.

This module implements the core extraction engine for the Human-in-the-Loop
learning system. It uses few-shot prompting with seed examples and previous
corrections to extract eligibility criteria from clinical trial data.
"""

import json
from typing import Any, Dict, List

import openai

from rwe_api.config import settings  # Centralized config


class EligibilityExtractor:
    """
    Extracts structured eligibility criteria from NCT clinical trial data.

    Uses GPT-4o-mini with few-shot examples to convert unstructured eligibility
    text into structured JSON matching our EligibilityExtraction schema.
    """

    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0):
        """
        Initialize the eligibility extractor.

        Args:
            model_name: OpenAI model to use for extraction
            temperature: Temperature for LLM (0.0 = deterministic)
        """
        self.model_name = model_name
        self.temperature = temperature

        # Use OPENROUTER_API_KEY (ALWAYS loaded from .env via settings)
        api_key = settings.OPENROUTER_API_KEY
        base_url = "https://openrouter.ai/api/v1" if api_key else None

        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def extract(
        self, nct_data: Dict[str, Any], examples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract structured eligibility criteria from NCT data.

        Args:
            nct_data: Full NCT JSON from ClinicalTrials.gov
            examples: List of correction examples for few-shot prompting

        Returns:
            Dictionary matching EligibilityExtraction schema
        """
        # Step 1: Extract eligibility section from NCT data
        eligibility_text = self._extract_eligibility_section(nct_data)

        if not eligibility_text:
            return self._empty_extraction()

        # Step 2: Build few-shot prompt
        prompt = self._build_prompt(eligibility_text, examples)

        # Step 3: Call LLM
        response = self._call_llm(prompt)

        # Step 4: Parse JSON response
        extraction = self._parse_json_response(response)

        # Step 5: Calculate confidence score
        confidence = self._calculate_confidence(extraction)
        extraction["confidence_score"] = confidence

        return extraction

    def _extract_eligibility_section(self, nct_data: Dict[str, Any]) -> str:
        """
        Extract the eligibility criteria text from NCT JSON.

        Args:
            nct_data: Full NCT JSON from ClinicalTrials.gov

        Returns:
            Raw eligibility criteria text, or empty string if not found
        """
        try:
            # Try new API format first (from langgraph-search fetcher)
            if "eligibility" in nct_data:
                eligibility = nct_data.get("eligibility", {})
                if isinstance(eligibility, dict):
                    eligibility_criteria = eligibility.get("eligibilityCriteria", "")
                    if eligibility_criteria:
                        return eligibility_criteria.strip()

            # Fallback to old API format (protocolSection)
            eligibility_module = nct_data.get("protocolSection", {}).get(
                "eligibilityModule", {}
            )
            eligibility_criteria = eligibility_module.get("eligibilityCriteria", "")
            return eligibility_criteria.strip()
        except (KeyError, AttributeError):
            return ""

    def _build_prompt(self, eligibility_text: str, examples: List[Dict[str, Any]]) -> str:
        """
        Build a few-shot prompt for the LLM.

        Args:
            eligibility_text: Raw eligibility criteria text to extract
            examples: List of correction examples (seed or user corrections)

        Returns:
            Complete prompt string for the LLM
        """
        system_message = """You are an expert medical data extractor. Your task is to extract eligibility criteria from clinical trial text and convert them into structured JSON format.

For each criterion, identify:
- id: Unique identifier (e.g., "inc_1", "exc_1")
- type: "inclusion" or "exclusion"
- key: The main concept (e.g., "Age", "ECOG Performance Status", "Hemoglobin")
- operator: One of: ">=", "<=", "==", "!=", "in", "not_in", "between", "contains"
- value: The threshold or target value (number, string, or list)
- unit: The unit if applicable (e.g., "years", "g/dL")
- original_text: The original text snippet

Output JSON format:
{
  "inclusion": [...],
  "exclusion": [...]
}"""

        # Add few-shot examples
        few_shot_examples = ""
        for i, example in enumerate(examples[:5], 1):  # Use up to 5 examples
            nct_id = example.get("nct_id", f"Example {i}")
            corrected = example.get("extraction", {}).get("human_corrected", {})

            few_shot_examples += f"\n\n--- Example {i} (NCT: {nct_id}) ---\n"
            few_shot_examples += f"Input:\n{self._get_example_original_text(corrected)}\n\n"
            few_shot_examples += f"Output:\n{json.dumps(corrected, indent=2)}\n"

        # Build final prompt
        prompt = f"""{system_message}

{few_shot_examples}

--- Now extract from the following text ---
Input:
{eligibility_text}

Output (JSON only, no explanation):
"""

        return prompt

    def _get_example_original_text(self, extraction: Dict[str, Any]) -> str:
        """Get concatenated original_text from an extraction for few-shot examples."""
        texts = []
        for criterion in extraction.get("inclusion", []):
            texts.append(criterion.get("original_text", ""))
        for criterion in extraction.get("exclusion", []):
            texts.append(criterion.get("original_text", ""))
        return "\n".join(filter(None, texts))

    def _call_llm(self, prompt: str) -> str:
        """
        Call OpenAI API to perform extraction.

        Args:
            prompt: Complete prompt string

        Returns:
            Raw LLM response text
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )

        return response.choices[0].message.content

    def _parse_json_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured dictionary.

        Args:
            raw_response: Raw text response from LLM

        Returns:
            Parsed extraction dictionary
        """
        try:
            extraction = json.loads(raw_response)

            # Normalize operators to match schema
            extraction = self._normalize_operators(extraction)

            return extraction
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response: {e}")
            print(f"Raw response: {raw_response[:500]}")
            return self._empty_extraction()

    def _normalize_operators(self, extraction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize operator values to match schema constraints.

        Fixes common LLM mistakes like '>' -> '>=' and '<' -> '<='.

        Args:
            extraction: Parsed extraction dictionary

        Returns:
            Extraction with normalized operators
        """
        operator_mapping = {
            ">": ">=",
            "<": "<=",
            "=": "==",
            "equals": "==",
            "not equals": "!=",
            "not equal": "!=",
        }

        for criterion_type in ["inclusion", "exclusion"]:
            if criterion_type in extraction:
                for criterion in extraction[criterion_type]:
                    if "operator" in criterion:
                        original_op = criterion["operator"]
                        normalized_op = operator_mapping.get(original_op, original_op)
                        criterion["operator"] = normalized_op

        return extraction

    def _calculate_confidence(self, extraction: Dict[str, Any]) -> float:
        """
        Calculate confidence score for the extraction.

        Heuristics:
        - Penalty if inclusion is empty
        - Penalty if criteria have very short text
        - Bonus if all criteria have proper structure

        Args:
            extraction: Parsed extraction dictionary

        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_score = 0.8

        inclusion = extraction.get("inclusion", [])
        exclusion = extraction.get("exclusion", [])

        # Penalty if inclusion is empty
        if len(inclusion) == 0:
            base_score -= 0.3

        # Penalty for very short original_text (likely poor extraction)
        all_criteria = inclusion + exclusion
        if all_criteria:
            avg_text_length = sum(
                len(c.get("original_text", "")) for c in all_criteria
            ) / len(all_criteria)
            if avg_text_length < 10:
                base_score -= 0.2

        # Bonus if all criteria have required fields
        if all_criteria:
            required_fields = ["id", "type", "key", "operator", "value", "original_text"]
            all_valid = all(
                all(field in c for field in required_fields) for c in all_criteria
            )
            if all_valid:
                base_score += 0.2

        return max(0.0, min(1.0, base_score))

    def _empty_extraction(self) -> Dict[str, Any]:
        """Return an empty extraction structure."""
        return {
            "inclusion": [],
            "exclusion": [],
            "confidence_score": 0.0,
        }
